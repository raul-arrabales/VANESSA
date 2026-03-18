CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY,
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_kind TEXT NOT NULL DEFAULT 'plain',
    title TEXT NOT NULL,
    title_source TEXT NOT NULL DEFAULT 'auto',
    model_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chat_conversations_kind_check'
    ) THEN
        ALTER TABLE chat_conversations
        ADD CONSTRAINT chat_conversations_kind_check
        CHECK (conversation_kind IN ('plain', 'knowledge'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chat_conversations_title_source_check'
    ) THEN
        ALTER TABLE chat_conversations
        ADD CONSTRAINT chat_conversations_title_source_check
        CHECK (title_source IN ('auto', 'manual'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS chat_conversations_owner_kind_updated_idx
    ON chat_conversations (owner_user_id, conversation_kind, updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    message_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chat_messages_role_check'
    ) THEN
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_role_check
        CHECK (role IN ('user', 'assistant'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_conversation_index_unique_idx
    ON chat_messages (conversation_id, message_index);

CREATE INDEX IF NOT EXISTS chat_messages_conversation_created_idx
    ON chat_messages (conversation_id, created_at ASC);
