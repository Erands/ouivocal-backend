-- REVIEW ONLY: transactional migration for a brand-new dedicated OuiVocal DB.
BEGIN;
CREATE FUNCTION ouivocal_set_updated_at() RETURNS trigger AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;
CREATE TABLE users (id UUID PRIMARY KEY, ouivocal_id VARCHAR(30) NOT NULL, ouivocal_id_normalized VARCHAR(30) NOT NULL UNIQUE, email VARCHAR(254) NOT NULL, email_normalized VARCHAR(254) NOT NULL UNIQUE, password_hash TEXT NOT NULL, full_name VARCHAR(120) NOT NULL, avatar_url TEXT, bio VARCHAR(500), location VARCHAR(120), phone_e164 VARCHAR(32) UNIQUE, email_verified_at TIMESTAMPTZ, phone_verified_at TIMESTAMPTZ, identity_verified_at TIMESTAMPTZ, account_status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK(account_status IN ('active','suspended','deleted')), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), last_seen_at TIMESTAMPTZ, CHECK(ouivocal_id ~ '^[A-Za-z0-9_]{3,30}$'), CHECK(ouivocal_id_normalized=lower(ouivocal_id)), CHECK(email_normalized=lower(email)));
CREATE TABLE user_language_preferences (user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, interface_language CHAR(2) NOT NULL CHECK(interface_language IN('en','fr','es','zh','ru','ar')), spoken_language CHAR(2) NOT NULL CHECK(spoken_language IN('en','fr','es','zh','ru','ar')), translation_source_language CHAR(2) NOT NULL CHECK(translation_source_language IN('en','fr','es','zh','ru','ar')), translation_target_language CHAR(2) NOT NULL CHECK(translation_target_language IN('en','fr','es','zh','ru','ar')), auto_detect_language BOOLEAN NOT NULL DEFAULT TRUE, text_translation_enabled BOOLEAN NOT NULL DEFAULT TRUE, voice_note_translation_enabled BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE contacts (id UUID PRIMARY KEY, lower_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, higher_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, requester_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, addressee_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, relationship_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(relationship_status IN('pending','accepted','rejected','blocked')), blocked_by_user_id UUID REFERENCES users(id) ON DELETE RESTRICT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), accepted_at TIMESTAMPTZ, UNIQUE(lower_user_id,higher_user_id), CHECK(lower_user_id<higher_user_id), CHECK(requester_user_id IN(lower_user_id,higher_user_id) AND addressee_user_id IN(lower_user_id,higher_user_id) AND requester_user_id<>addressee_user_id), CHECK((relationship_status='blocked' AND blocked_by_user_id IN(lower_user_id,higher_user_id)) OR (relationship_status<>'blocked' AND blocked_by_user_id IS NULL)));
CREATE TABLE conversations (id UUID PRIMARY KEY, conversation_type VARCHAR(20) NOT NULL DEFAULT 'direct' CHECK(conversation_type IN('direct','group')), created_by_user_id UUID NOT NULL REFERENCES users(id), direct_lower_user_id UUID REFERENCES users(id), direct_higher_user_id UUID REFERENCES users(id), default_source_language CHAR(2) CHECK(default_source_language IN('en','fr','es','zh','ru','ar')), default_target_language CHAR(2) CHECK(default_target_language IN('en','fr','es','zh','ru','ar')), auto_detect_language BOOLEAN, text_translation_enabled BOOLEAN, voice_note_translation_enabled BOOLEAN, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(direct_lower_user_id,direct_higher_user_id), CHECK((conversation_type='direct' AND direct_lower_user_id IS NOT NULL AND direct_higher_user_id IS NOT NULL AND direct_lower_user_id<direct_higher_user_id) OR (conversation_type='group' AND direct_lower_user_id IS NULL AND direct_higher_user_id IS NULL)));
CREATE TABLE conversation_members (id UUID PRIMARY KEY, conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, member_role VARCHAR(20) NOT NULL DEFAULT 'member' CHECK(member_role IN('owner','member')), joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), left_at TIMESTAMPTZ, last_read_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(conversation_id,user_id));
ALTER TABLE conversations ADD CONSTRAINT conversations_creator_is_member FOREIGN KEY(id,created_by_user_id) REFERENCES conversation_members(conversation_id,user_id) DEFERRABLE INITIALLY DEFERRED;
CREATE FUNCTION ouivocal_validate_direct_conversation_members() RETURNS trigger AS $$
DECLARE
  checked_conversation_id UUID;
  conversation_kind VARCHAR(20);
  direct_lower UUID;
  direct_higher UUID;
  creator UUID;
  member_count INTEGER;
  participant_count INTEGER;
  creator_is_direct_participant BOOLEAN;
  creator_is_owner BOOLEAN;
BEGIN
  IF TG_TABLE_NAME = 'conversation_members' THEN
    checked_conversation_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.conversation_id ELSE NEW.conversation_id END;
  ELSE
    checked_conversation_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
  END IF;

  SELECT conversation_type, direct_lower_user_id, direct_higher_user_id, created_by_user_id
    INTO conversation_kind, direct_lower, direct_higher, creator
    FROM conversations
   WHERE id = checked_conversation_id;

  IF NOT FOUND OR conversation_kind <> 'direct' THEN
    RETURN NULL;
  END IF;

  SELECT COUNT(*),
         COUNT(*) FILTER (WHERE user_id IN (direct_lower, direct_higher)),
         COALESCE(BOOL_OR(user_id = creator AND member_role = 'owner'), FALSE)
    INTO member_count, participant_count, creator_is_owner
    FROM conversation_members
   WHERE conversation_id = checked_conversation_id;

  creator_is_direct_participant := creator IN (direct_lower, direct_higher);
  IF member_count <> 2
     OR participant_count <> 2
     OR NOT creator_is_direct_participant
     OR NOT creator_is_owner THEN
    RAISE EXCEPTION 'direct conversation % must contain exactly its two participants and an owner creator', checked_conversation_id;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER conversation_members_direct_invariants AFTER INSERT OR UPDATE OR DELETE ON conversation_members DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ouivocal_validate_direct_conversation_members();
CREATE CONSTRAINT TRIGGER conversations_direct_invariants AFTER INSERT OR UPDATE OR DELETE ON conversations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ouivocal_validate_direct_conversation_members();
CREATE TABLE refresh_tokens (id UUID PRIMARY KEY, token_family_id UUID NOT NULL, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, token_digest CHAR(64) NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ, replaced_by_token_id UUID REFERENCES refresh_tokens(id) ON DELETE SET NULL, reuse_detected_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), last_used_at TIMESTAMPTZ, user_agent VARCHAR(512), ip_address INET);
CREATE INDEX users_ouivocal_id_search_idx ON users(ouivocal_id_normalized); CREATE INDEX contacts_participant_idx ON contacts(lower_user_id,higher_user_id); CREATE INDEX conversation_members_user_idx ON conversation_members(user_id,joined_at DESC); CREATE INDEX refresh_tokens_active_idx ON refresh_tokens(user_id,expires_at) WHERE revoked_at IS NULL; CREATE INDEX refresh_tokens_family_idx ON refresh_tokens(token_family_id);
CREATE TRIGGER users_updated BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION ouivocal_set_updated_at(); CREATE TRIGGER preferences_updated BEFORE UPDATE ON user_language_preferences FOR EACH ROW EXECUTE FUNCTION ouivocal_set_updated_at(); CREATE TRIGGER contacts_updated BEFORE UPDATE ON contacts FOR EACH ROW EXECUTE FUNCTION ouivocal_set_updated_at(); CREATE TRIGGER conversations_updated BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION ouivocal_set_updated_at(); CREATE TRIGGER members_updated BEFORE UPDATE ON conversation_members FOR EACH ROW EXECUTE FUNCTION ouivocal_set_updated_at(); CREATE TRIGGER tokens_updated BEFORE UPDATE ON refresh_tokens FOR EACH ROW EXECUTE FUNCTION ouivocal_set_updated_at();
COMMIT;
