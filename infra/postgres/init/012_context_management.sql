CREATE TABLE IF NOT EXISTS context_knowledge_bases (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    index_name TEXT NOT NULL UNIQUE,
    backing_provider_instance_id UUID NOT NULL REFERENCES platform_provider_instances(id) ON DELETE RESTRICT,
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
    ADD COLUMN IF NOT EXISTS backing_provider_instance_id UUID REFERENCES platform_provider_instances(id) ON DELETE RESTRICT;
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

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'context_knowledge_bases'
          AND column_name = 'backing_provider_key'
    ) THEN
        IF EXISTS (
            SELECT 1
            FROM (
                SELECT kb.id
                FROM context_knowledge_bases kb
                LEFT JOIN platform_provider_instances i ON i.provider_key = kb.backing_provider_key
                LEFT JOIN platform_provider_families f ON f.provider_key = i.provider_key
                WHERE kb.backing_provider_instance_id IS NULL
                GROUP BY kb.id
                HAVING COUNT(*) FILTER (WHERE f.capability_key = 'vector_store') <> 1
            ) unresolved
        ) THEN
            RAISE EXCEPTION
                'Unable to backfill context_knowledge_bases.backing_provider_instance_id because one or more rows have zero or multiple matching vector-store provider instances.';
        END IF;

        UPDATE context_knowledge_bases kb
        SET backing_provider_instance_id = resolved.provider_instance_id
        FROM (
            SELECT
                kb_inner.id AS knowledge_base_id,
                i.id AS provider_instance_id
            FROM context_knowledge_bases kb_inner
            JOIN platform_provider_instances i ON i.provider_key = kb_inner.backing_provider_key
            JOIN platform_provider_families f ON f.provider_key = i.provider_key
            WHERE kb_inner.backing_provider_instance_id IS NULL
              AND f.capability_key = 'vector_store'
        ) resolved
        WHERE kb.id = resolved.knowledge_base_id
          AND kb.backing_provider_instance_id IS NULL;
    END IF;
END
$$;

ALTER TABLE context_knowledge_bases
    ALTER COLUMN backing_provider_instance_id SET NOT NULL;

DROP INDEX IF EXISTS context_knowledge_bases_backing_provider_key_idx;

ALTER TABLE context_knowledge_bases
    DROP COLUMN IF EXISTS backing_provider_key;

CREATE INDEX IF NOT EXISTS context_knowledge_bases_backing_provider_instance_idx
    ON context_knowledge_bases (backing_provider_instance_id);

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
