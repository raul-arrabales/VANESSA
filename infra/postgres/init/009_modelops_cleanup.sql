ALTER TABLE model_registry
    ADD COLUMN IF NOT EXISTS owner_type TEXT;

UPDATE model_registry
SET
    owner_type = COALESCE(
        NULLIF(owner_type, ''),
        CASE
            WHEN lower(COALESCE(origin_scope, '')) = 'platform' THEN 'platform'
            WHEN owner_user_id IS NULL THEN 'platform'
            ELSE 'user'
        END
    ),
    owner_user_id = CASE
        WHEN COALESCE(
            NULLIF(owner_type, ''),
            CASE
                WHEN lower(COALESCE(origin_scope, '')) = 'platform' THEN 'platform'
                WHEN owner_user_id IS NULL THEN 'platform'
                ELSE 'user'
            END
        ) = 'platform'
        THEN NULL
        ELSE COALESCE(owner_user_id, registered_by_user_id, created_by_user_id)
    END,
    visibility_scope = COALESCE(
        NULLIF(visibility_scope, ''),
        CASE lower(COALESCE(access_scope, ''))
            WHEN 'global' THEN 'platform'
            WHEN 'assigned' THEN 'user'
            ELSE CASE
                WHEN lower(COALESCE(origin_scope, '')) = 'platform' THEN 'private'
                ELSE 'private'
            END
        END
    ),
    task_key = COALESCE(
        NULLIF(task_key, ''),
        CASE lower(COALESCE(model_type, ''))
            WHEN 'embedding' THEN 'embeddings'
            WHEN 'llm' THEN 'llm'
            ELSE 'llm'
        END
    ),
    category = COALESCE(
        NULLIF(category, ''),
        CASE
            WHEN lower(COALESCE(model_type, '')) = 'embedding' THEN 'predictive'
            WHEN lower(COALESCE(task_key, '')) IN ('embeddings', 'ocr', 'vision', 'speech_to_text', 'classification', 'regression', 'ranking', 'reranking', 'moderation') THEN 'predictive'
            ELSE 'generative'
        END
    )
WHERE
    owner_type IS NULL
    OR visibility_scope IS NULL
    OR task_key IS NULL
    OR category IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_owner_type_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_owner_type_check
        CHECK (owner_type IN ('platform', 'user'));
    END IF;
END
$$;

ALTER TABLE model_registry ALTER COLUMN owner_type SET DEFAULT 'platform';

ALTER TABLE model_registry DROP CONSTRAINT IF EXISTS model_registry_model_type_check;
ALTER TABLE model_registry DROP CONSTRAINT IF EXISTS model_registry_origin_scope_check;
ALTER TABLE model_registry DROP CONSTRAINT IF EXISTS model_registry_access_scope_check;

DROP INDEX IF EXISTS model_registry_origin_access_idx;

ALTER TABLE model_registry
    DROP COLUMN IF EXISTS model_type,
    DROP COLUMN IF EXISTS origin_scope,
    DROP COLUMN IF EXISTS access_scope;
