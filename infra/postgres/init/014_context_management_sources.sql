CREATE TABLE IF NOT EXISTS context_knowledge_sources (
    id UUID PRIMARY KEY,
    knowledge_base_id UUID NOT NULL REFERENCES context_knowledge_bases(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL DEFAULT 'local_directory',
    display_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    include_globs JSONB NOT NULL DEFAULT '[]'::jsonb,
    exclude_globs JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lifecycle_state TEXT NOT NULL DEFAULT 'active',
    last_sync_status TEXT NOT NULL DEFAULT 'idle',
    last_sync_at TIMESTAMPTZ,
    last_sync_error TEXT,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'local_directory';
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS relative_path TEXT;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS include_globs JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS exclude_globs JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS lifecycle_state TEXT NOT NULL DEFAULT 'active';
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS last_sync_status TEXT NOT NULL DEFAULT 'idle';
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS last_sync_error TEXT;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE context_knowledge_sources
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_sources_source_type_check'
    ) THEN
        ALTER TABLE context_knowledge_sources
        ADD CONSTRAINT context_knowledge_sources_source_type_check
        CHECK (source_type IN ('local_directory'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_sources_lifecycle_state_check'
    ) THEN
        ALTER TABLE context_knowledge_sources
        ADD CONSTRAINT context_knowledge_sources_lifecycle_state_check
        CHECK (lifecycle_state IN ('active', 'archived'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_sources_last_sync_status_check'
    ) THEN
        ALTER TABLE context_knowledge_sources
        ADD CONSTRAINT context_knowledge_sources_last_sync_status_check
        CHECK (last_sync_status IN ('idle', 'syncing', 'ready', 'error'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS context_knowledge_sources_unique_path_idx
    ON context_knowledge_sources (knowledge_base_id, relative_path);

CREATE INDEX IF NOT EXISTS context_knowledge_sources_kb_idx
    ON context_knowledge_sources (knowledge_base_id, created_at DESC);

CREATE TABLE IF NOT EXISTS context_knowledge_sync_runs (
    id UUID PRIMARY KEY,
    knowledge_base_id UUID NOT NULL REFERENCES context_knowledge_bases(id) ON DELETE CASCADE,
    source_id UUID REFERENCES context_knowledge_sources(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'syncing',
    scanned_file_count INTEGER NOT NULL DEFAULT 0,
    changed_file_count INTEGER NOT NULL DEFAULT 0,
    deleted_file_count INTEGER NOT NULL DEFAULT 0,
    created_document_count INTEGER NOT NULL DEFAULT 0,
    updated_document_count INTEGER NOT NULL DEFAULT 0,
    deleted_document_count INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL
);

ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS source_id UUID REFERENCES context_knowledge_sources(id) ON DELETE CASCADE;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'syncing';
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS scanned_file_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS changed_file_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS deleted_file_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS created_document_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS updated_document_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS deleted_document_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS error_summary TEXT;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;
ALTER TABLE context_knowledge_sync_runs
    ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_sync_runs_status_check'
    ) THEN
        ALTER TABLE context_knowledge_sync_runs
        ADD CONSTRAINT context_knowledge_sync_runs_status_check
        CHECK (status IN ('syncing', 'ready', 'error'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS context_knowledge_sync_runs_kb_idx
    ON context_knowledge_sync_runs (knowledge_base_id, started_at DESC);

ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS source_id UUID REFERENCES context_knowledge_sources(id) ON DELETE SET NULL;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS source_path TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS source_document_key TEXT;
ALTER TABLE context_documents
    ADD COLUMN IF NOT EXISTS managed_by_source BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS context_documents_source_idx
    ON context_documents (knowledge_base_id, source_id, source_document_key);
