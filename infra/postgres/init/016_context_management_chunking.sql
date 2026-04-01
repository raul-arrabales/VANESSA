ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS chunking_strategy TEXT NOT NULL DEFAULT 'fixed_length';

ALTER TABLE context_knowledge_bases
    ADD COLUMN IF NOT EXISTS chunking_config_json JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE context_knowledge_bases
SET
    chunking_strategy = COALESCE(NULLIF(chunking_strategy, ''), 'fixed_length'),
    chunking_config_json = jsonb_strip_nulls(
        jsonb_build_object(
            'unit', COALESCE(NULLIF(chunking_config_json->>'unit', ''), 'tokens'),
            'chunk_length', COALESCE(NULLIF(chunking_config_json->>'chunk_length', '')::INTEGER, 300),
            'chunk_overlap', COALESCE(NULLIF(chunking_config_json->>'chunk_overlap', '')::INTEGER, 60)
        )
    )
WHERE
    chunking_strategy IS DISTINCT FROM 'fixed_length'
    OR chunking_config_json IS NULL
    OR chunking_config_json = '{}'::jsonb
    OR NULLIF(chunking_config_json->>'unit', '') IS NULL
    OR NULLIF(chunking_config_json->>'chunk_length', '') IS NULL
    OR NULLIF(chunking_config_json->>'chunk_overlap', '') IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'context_knowledge_bases_chunking_strategy_check'
    ) THEN
        ALTER TABLE context_knowledge_bases
        ADD CONSTRAINT context_knowledge_bases_chunking_strategy_check
        CHECK (chunking_strategy IN ('fixed_length'));
    END IF;
END
$$;
