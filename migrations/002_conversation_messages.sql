BEGIN;

CREATE TABLE IF NOT EXISTS identity_schema_migrations (
    version VARCHAR(120) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM identity_schema_migrations
        WHERE version = '002_conversation_messages'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'conversation_messages'
    ) THEN
        RAISE EXCEPTION 'migration 002_conversation_messages is recorded but its table is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM identity_schema_migrations
        WHERE version = '002_conversation_messages'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'conversation_messages'
    ) THEN
        RAISE EXCEPTION 'conversation_messages exists without migration 002_conversation_messages recorded';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM identity_schema_migrations
        WHERE version = '002_conversation_messages'
    ) THEN
        CREATE TABLE conversation_messages (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            sender_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            original_text TEXT NOT NULL CHECK (char_length(original_text) BETWEEN 1 AND 4000),
            translated_text TEXT,
            source_language CHAR(2) NOT NULL CHECK (source_language IN ('en','fr','es','zh','ru','ar')),
            target_language CHAR(2) NOT NULL CHECK (target_language IN ('en','fr','es','zh','ru','ar')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX conversation_messages_history_idx
            ON conversation_messages(conversation_id, created_at, id);

        CREATE INDEX conversation_messages_sender_idx
            ON conversation_messages(sender_user_id, created_at DESC);

        CREATE FUNCTION ouivocal_validate_message_sender() RETURNS trigger AS $trigger$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM conversation_members
                WHERE conversation_id = NEW.conversation_id
                  AND user_id = NEW.sender_user_id
                  AND left_at IS NULL
            ) THEN
                RAISE EXCEPTION 'message sender must be an active conversation member';
            END IF;
            RETURN NEW;
        END;
        $trigger$ LANGUAGE plpgsql;

        CREATE TRIGGER conversation_messages_sender_member
            BEFORE INSERT OR UPDATE OF conversation_id, sender_user_id ON conversation_messages
            FOR EACH ROW EXECUTE FUNCTION ouivocal_validate_message_sender();

        INSERT INTO identity_schema_migrations(version)
        VALUES ('002_conversation_messages');
    END IF;
END;
$$;

COMMIT;
