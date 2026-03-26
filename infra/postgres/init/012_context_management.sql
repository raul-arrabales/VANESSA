CREATE TABLE IF NOT EXISTS context_knowledge_bases (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    index_name TEXT NOT NULL UNIQUE,
    backing_provider_key TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'active',
    sync_status TEXT NOT NULL DEFAULT 'ready',
    schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    document_count INTEGER NOT NULL DEFAULT 0,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS index_name TEXT;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS backing_provider_key TEXT;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS lifecycle_state TEXT NOT NULL DEFAULT 'active';
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS sync_status TEXT NOT NULL DEFAULT 'ready';
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS schema_json JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS document_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_bases_lifecycle_state_check'
    ) THEN
        ALTER TABLE context_knowledge_bases
        ADD CONSTRAINT context_knowledge_bases_lifecycle_state_check
        CHECK (lifecycle_state IN ('active', 'archived'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_bases_sync_status_check'
    ) THEN
        ALTER TABLE context_knowledge_bases
        ADD CONSTRAINT context_knowledge_bases_sync_status_check
        CHECK (sync_status IN ('ready', 'syncing', 'error'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS context_knowledge_bases_backing_provider_key_idx
    ON context_knowledge_bases (backing_provider_key);

CREATE TABLE IF NOT EXISTS context_documents (
    id UUID PRIMARY KEY,
    knowledge_base_id UUID NOT NULL REFERENCES context_knowledge_bases(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT,
    uri TEXT,
    text TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS knowledge_base_id UUID REFERENCES context_knowledge_bases(id) ON DELETE CASCADE;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS source_type TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS source_name TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS uri TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS text TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS chunk_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS context_documents_knowledge_base_id_idx
    ON context_documents (knowledge_base_id, created_at DESC);

ALTER TABLE platform_binding_resources
    ADD COLUMN IF NOT EXISTS knowledge_base_id UUID REFERENCES context_knowledge_bases(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS platform_binding_resources_knowledge_base_idx
    ON platform_binding_resources (knowledge_base_id);
