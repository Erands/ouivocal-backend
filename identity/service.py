"""Inactive application service; repository calls are parameterized and transactional."""
from datetime import UTC, datetime
from uuid import UUID

from identity.security import hash_password,password_matches,issue_access_token,issue_refresh_token,token_digest
from identity.models import public_search_result
from identity import validation
from identity.validation import normalize_email,normalize_ouivocal_id,require_password,optional_text

USER_SEARCH_MINIMUM_LENGTH = 2
USER_SEARCH_LIMIT = 20
MESSAGE_HISTORY_LIMIT = 100
MESSAGE_TEXT_MAXIMUM_LENGTH = 4000

class AuthorizationError(PermissionError):
 pass

def require_user_id(value, field_name):
 try: return UUID(str(value))
 except (TypeError, ValueError, AttributeError): raise validation.ValidationError(f'{field_name} must be a UUID')

def normalize_user_search_query(value):
 if not isinstance(value,str): raise validation.ValidationError('Search query is required')
 query=value.strip()
 if len(query)<USER_SEARCH_MINIMUM_LENGTH: raise validation.ValidationError('Search query must contain at least 2 characters')
 if len(query)>120: raise validation.ValidationError('Search query is too long')
 return query

def conversation_languages_for_user(conversation, user_id):
 source=conversation.get('default_source_language'); target=conversation.get('default_target_language')
 if conversation.get('created_by_user_id') != user_id:
  return target,source
 return source,target

def public_message(row,current_user_id):
 return {'id':str(row['id']),'original':row['original_text'],'translated':row.get('translated_text'),
         'source_language':row['source_language'],'target_language':row['target_language'],
         'created_at':row['created_at'].isoformat(),'is_mine':row['sender_user_id']==current_user_id}
def register(repo,data):
 email=normalize_email(data.get('email')); oui=normalize_ouivocal_id(data.get('ouivocal_id')); name=optional_text(data.get('full_name'),'full_name',120)
 if not name or repo.by_email(email) or repo.by_oui(oui): raise ValueError('Identity already exists or is invalid')
 uid=repo.create_user({'email':data['email'].strip(),'email_norm':email,'ouivocal_id':data['ouivocal_id'].strip(),'oui':oui,'full_name':name,'password_hash':hash_password(require_password(data.get('password')))})
 return issue(repo,str(uid))
def issue(repo,uid,family=None):
 raw,digest,expires,token_id,family=issue_refresh_token(uid,family); repo.execute('INSERT INTO refresh_tokens(id,token_family_id,user_id,token_digest,expires_at) VALUES(%s,%s,%s,%s,%s)',(token_id,family,uid,digest,expires)); return {'access_token':issue_access_token(uid),'refresh_token':raw,'token_type':'Bearer'}
def login(repo,email,password):
 user=repo.by_email(normalize_email(email))
 if not user or not password_matches(user['password_hash'],password): raise PermissionError('Invalid credentials')
 return issue(repo,str(user['id']))
def refresh(repo,raw):
 row=repo.token(token_digest(raw))
 if not row: raise PermissionError('Invalid or reused refresh token')
 if row['revoked_at']:
  repo.revoke_family(row['token_family_id'])
  raise PermissionError('Invalid or reused refresh token')
 if row['expires_at'] <= datetime.now(UTC):
  raise PermissionError('Invalid or expired refresh token')
 repo.execute('UPDATE refresh_tokens SET revoked_at=NOW() WHERE id=%s',(row['id'],)); return issue(repo,str(row['user_id']),str(row['token_family_id']))

def search_users(repo,current_user_id,query):
 query=normalize_user_search_query(query)
 return {'results':[public_search_result(row) for row in repo.search_public_users(query,current_user_id,USER_SEARCH_LIMIT)]}

def contact_relationship(repo,current_user_id,other_user_id):
 current=require_user_id(current_user_id,'Authenticated user'); other=require_user_id(other_user_id,'user_id')
 if current == other: raise validation.ValidationError('A contact relationship requires another user')
 if not repo.user(current): raise PermissionError('Authenticated user is not active')
 if not repo.public_active_user(other): raise LookupError('User was not found or is inactive')
 contact=repo.contact_between(current,other)
 if not contact: return {'status':'none','direction':'none'}
 direction='outgoing' if contact['requester_user_id']==current else 'incoming'
 return {'id':str(contact['id']),'status':contact['relationship_status'],'direction':direction}

def create_contact_request(repo,current_user_id,data):
 requester=require_user_id(current_user_id,'Authenticated user'); addressee=require_user_id(data.get('user_id'),'user_id')
 if requester == addressee: raise validation.ValidationError('You cannot add yourself as a contact')
 if not repo.user(requester): raise PermissionError('Authenticated user is not active')
 if not repo.public_active_user(addressee): raise LookupError('User was not found or is inactive')
 contact,created=repo.create_contact_request(requester,addressee)
 if not contact or contact['relationship_status']=='blocked': raise LookupError('Contact request is unavailable')
 direction='outgoing' if contact['requester_user_id']==requester else 'incoming'
 return {'id':str(contact['id']),'status':contact['relationship_status'],'direction':direction,'created':created}

def respond_to_contact_request(repo,current_user_id,contact_id,status):
 addressee=require_user_id(current_user_id,'Authenticated user'); request_id=require_user_id(contact_id,'contact request id')
 if not repo.user(addressee): raise PermissionError('Authenticated user is not active')
 contact=repo.respond_to_contact_request(request_id,addressee,status)
 if not contact: raise LookupError('Pending contact request was not found')
 return {'id':str(contact['id']),'status':contact['relationship_status'],'direction':'incoming'}

def incoming_contact_requests(repo,current_user_id):
 addressee=require_user_id(current_user_id,'Authenticated user')
 if not repo.user(addressee): raise PermissionError('Authenticated user is not active')
 return {'requests':[{'id':str(row['contact_id']),'status':row['relationship_status'],'requester':public_search_result(row)} for row in repo.pending_contact_requests_for(addressee)]}

def list_direct_conversations(repo,current_user_id):
 current=require_user_id(current_user_id,'Authenticated user')
 if not repo.user(current): raise PermissionError('Authenticated user is not active')
 conversations=[]
 for row in repo.direct_conversations_for(current):
  source,target=conversation_languages_for_user(row,current)
  conversations.append({'conversation_id':str(row['conversation_id']),'participant':public_search_result(row),
                        'source_language':source,'target_language':target,'last_message':row.get('last_message'),
                        'last_message_at':row['last_message_at'].isoformat() if row.get('last_message_at') else None,
                        'unread_count':0})
 return {'conversations':conversations}

def conversation_messages(repo,current_user_id,conversation_id):
 current=require_user_id(current_user_id,'Authenticated user'); conversation=require_user_id(conversation_id,'conversation_id')
 if not repo.user(current): raise PermissionError('Authenticated user is not active')
 if not repo.conversation_for_member(conversation,current): raise AuthorizationError('Conversation access is not allowed')
 return {'messages':[public_message(row,current) for row in repo.conversation_messages_for_member(conversation,current,MESSAGE_HISTORY_LIMIT)]}

def create_conversation_message(repo,current_user_id,conversation_id,data):
 current=require_user_id(current_user_id,'Authenticated user'); conversation_id=require_user_id(conversation_id,'conversation_id')
 if not repo.user(current): raise PermissionError('Authenticated user is not active')
 original=optional_text(data.get('original'),'original',MESSAGE_TEXT_MAXIMUM_LENGTH)
 translated=optional_text(data.get('translated'),'translated',MESSAGE_TEXT_MAXIMUM_LENGTH)
 if not original: raise validation.ValidationError('original is required')
 conversation=repo.conversation_for_member(conversation_id,current)
 if not conversation: raise AuthorizationError('Conversation access is not allowed')
 source,target=conversation_languages_for_user(conversation,current)
 if data.get('source_language') != source or data.get('target_language') != target:
  raise AuthorizationError('Conversation language direction is not allowed')
 row=repo.create_conversation_message(conversation_id,current,original,translated,source,target)
 return {'message':public_message(row,current)}

def create_direct_conversation(repo,current_user_id,data):
 creator=require_user_id(current_user_id,'Authenticated user')
 participant_id=require_user_id(data.get('participant_id'),'participant_id')
 if creator == participant_id: raise validation.ValidationError('A conversation requires another participant')
 source_language=validation.require_language(data.get('my_language'),'my_language')
 target_language=validation.require_language(data.get('their_language'),'their_language')
 if not repo.user(creator): raise PermissionError('Authenticated user is not active')
 participant=repo.public_active_user(participant_id)
 if not participant: raise LookupError('Participant was not found or is inactive')
 if not repo.accepted_contact_exists(creator,participant_id): raise AuthorizationError('An accepted contact relationship is required')
 result=repo.direct_with_preferences(creator,participant_id,source_language,target_language)
 if len(result)==2:
  conversation_id,created=result
  conversation={'created_by_user_id':creator,'default_source_language':source_language,'default_target_language':target_language}
 else:
  conversation_id,created,conversation=result
 source_language,target_language=conversation_languages_for_user(conversation,creator)
 return {'conversation_id':str(conversation_id),'created':created,'participant':public_search_result(participant),'source_language':source_language,'target_language':target_language}
