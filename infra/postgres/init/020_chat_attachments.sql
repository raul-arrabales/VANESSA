CREATE TABLE IF NOT EXISTS chat_attachments (
    id UUID PRIMARY KEY,
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE SET NULL,
    message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
    attachment_kind TEXT NOT NULL DEFAULT 'image',
    mime_type TEXT NOT NULL,
    byte_size BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    storage_path TEXT NOT NULL,
    original_filename TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chat_attachments_kind_check CHECK (attachment_kind IN ('image')),
    CONSTRAINT chat_attachments_byte_size_check CHECK (byte_size > 0),
    CONSTRAINT chat_attachments_width_check CHECK (width IS NULL OR width > 0),
    CONSTRAINT chat_attachments_height_check CHECK (height IS NULL OR height > 0)
);

CREATE INDEX IF NOT EXISTS chat_attachments_owner_created_idx
    ON chat_attachments (owner_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS chat_attachments_conversation_idx
    ON chat_attachments (conversation_id);

CREATE INDEX IF NOT EXISTS chat_attachments_message_idx
    ON chat_attachments (message_id);
