ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;

ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS last_sync_error TEXT;

ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS last_sync_summary TEXT;
