"""Inactive application service; repository calls are parameterized and transactional."""
from datetime import UTC, datetime
from uuid import UUID

from identity.security import hash_password,password_matches,issue_access_token,issue_refresh_token,token_digest
from identity.models import public_search_result
from identity import validation
from identity.validation import normalize_email,normalize_ouivocal_id,require_password,optional_text

USER_SEARCH_MINIMUM_LENGTH = 2
USER_SEARCH_LIMIT = 20

def require_user_id(value, field_name):
 try: return UUID(str(value))
 except (TypeError, ValueError, AttributeError): raise validation.ValidationError(f'{field_name} must be a UUID')

def normalize_user_search_query(value):
 if not isinstance(value,str): raise validation.ValidationError('Search query is required')
 query=value.strip()
 if len(query)<USER_SEARCH_MINIMUM_LENGTH: raise validation.ValidationError('Search query must contain at least 2 characters')
 if len(query)>120: raise validation.ValidationError('Search query is too long')
 return query
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

def create_direct_conversation(repo,current_user_id,data):
 creator=require_user_id(current_user_id,'Authenticated user')
 participant_id=require_user_id(data.get('participant_id'),'participant_id')
 if creator == participant_id: raise validation.ValidationError('A conversation requires another participant')
 source_language=validation.require_language(data.get('my_language'),'my_language')
 target_language=validation.require_language(data.get('their_language'),'their_language')
 if not repo.user(creator): raise PermissionError('Authenticated user is not active')
 participant=repo.public_active_user(participant_id)
 if not participant: raise LookupError('Participant was not found or is inactive')
 conversation_id,created=repo.direct_with_preferences(creator,participant_id,source_language,target_language)
 return {'conversation_id':str(conversation_id),'created':created,'participant':public_search_result(participant)}
