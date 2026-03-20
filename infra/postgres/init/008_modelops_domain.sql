CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE model_registry
    ADD COLUMN IF NOT EXISTS node_id TEXT,
    ADD COLUMN IF NOT EXISTS global_model_id TEXT,
    ADD COLUMN IF NOT EXISTS task_key TEXT,
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS hosting_kind TEXT,
    ADD COLUMN IF NOT EXISTS runtime_mode_policy TEXT,
    ADD COLUMN IF NOT EXISTS lifecycle_state TEXT,
    ADD COLUMN IF NOT EXISTS visibility_scope TEXT,
    ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS dependency_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS current_config_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS last_validation_config_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS is_validation_current BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_validation_status TEXT,
    ADD COLUMN IF NOT EXISTS last_validated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_validation_error JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS model_version TEXT,
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS revision TEXT,
    ADD COLUMN IF NOT EXISTS checksum TEXT;

UPDATE model_registry
SET
    node_id = COALESCE(NULLIF(node_id, ''), 'local'),
    global_model_id = COALESCE(NULLIF(global_model_id, ''), concat(COALESCE(NULLIF(node_id, ''), 'local'), ':', model_id)),
    task_key = COALESCE(
        NULLIF(task_key, ''),
        CASE lower(COALESCE(model_type, ''))
            WHEN 'embedding' THEN 'embeddings'
            WHEN 'llm' THEN 'llm'
            ELSE CASE
                WHEN lower(COALESCE(provider, '')) IN ('openai', 'anthropic', 'hf', 'huggingface', 'vllm', 'openai_compatible', 'local', 'local_filesystem') THEN 'llm'
                ELSE 'llm'
            END
        END
    ),
    category = COALESCE(
        NULLIF(category, ''),
        CASE
            WHEN lower(COALESCE(model_type, '')) = 'embedding' THEN 'predictive'
            ELSE 'generative'
        END
    ),
    hosting_kind = COALESCE(
        NULLIF(hosting_kind, ''),
        CASE lower(COALESCE(backend_kind, ''))
            WHEN 'local' THEN 'local'
            ELSE 'cloud'
        END
    ),
    runtime_mode_policy = COALESCE(
        NULLIF(runtime_mode_policy, ''),
        CASE lower(COALESCE(backend_kind, ''))
            WHEN 'local' THEN 'online_offline'
            ELSE 'online_only'
        END
    ),
    visibility_scope = COALESCE(
        NULLIF(visibility_scope, ''),
        CASE lower(COALESCE(access_scope, ''))
            WHEN 'global' THEN 'platform'
            WHEN 'assigned' THEN 'user'
            ELSE 'private'
        END
    ),
    owner_user_id = COALESCE(owner_user_id, registered_by_user_id, created_by_user_id),
    lifecycle_state = COALESCE(
        NULLIF(lifecycle_state, ''),
        CASE
            WHEN COALESCE(is_enabled, TRUE) = TRUE AND COALESCE(status, 'available') = 'available' THEN 'active'
            WHEN COALESCE(status, 'available') = 'archived' THEN 'unregistered'
            ELSE 'registered'
        END
    ),
    is_validation_current = COALESCE(
        is_validation_current,
        CASE
            WHEN COALESCE(is_enabled, TRUE) = TRUE AND COALESCE(status, 'available') = 'available' THEN TRUE
            ELSE FALSE
        END
    ),
    last_validation_status = COALESCE(
        NULLIF(last_validation_status, ''),
        CASE
            WHEN COALESCE(is_enabled, TRUE) = TRUE AND COALESCE(status, 'available') = 'available' THEN 'success'
            ELSE NULL
        END
    ),
    last_validated_at = COALESCE(
        last_validated_at,
        CASE
            WHEN COALESCE(is_enabled, TRUE) = TRUE AND COALESCE(status, 'available') = 'available' THEN updated_at
            ELSE NULL
        END
    ),
    source = COALESCE(NULLIF(source, ''), source_id),
    checksum = COALESCE(NULLIF(checksum, ''), NULLIF(metadata->>'checksum', '')),
    revision = COALESCE(NULLIF(revision, ''), NULLIF(metadata->>'revision', '')),
    model_version = COALESCE(NULLIF(model_version, ''), NULLIF(metadata->>'model_version', ''))
WHERE
    node_id IS NULL
    OR global_model_id IS NULL
    OR task_key IS NULL
    OR category IS NULL
    OR hosting_kind IS NULL
    OR runtime_mode_policy IS NULL
    OR visibility_scope IS NULL
    OR lifecycle_state IS NULL
    OR owner_user_id IS NULL
    OR source IS NULL;

ALTER TABLE model_registry ALTER COLUMN node_id SET DEFAULT 'local';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_category_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_category_check
        CHECK (category IN ('predictive', 'generative'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_hosting_kind_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_hosting_kind_check
        CHECK (hosting_kind IN ('local', 'cloud'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_runtime_mode_policy_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_runtime_mode_policy_check
        CHECK (runtime_mode_policy IN ('online_only', 'online_offline'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_lifecycle_state_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_lifecycle_state_check
        CHECK (lifecycle_state IN ('created', 'registered', 'validated', 'active', 'inactive', 'unregistered', 'deleted'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_visibility_scope_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_visibility_scope_check
        CHECK (visibility_scope IN ('private', 'user', 'group', 'platform'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_last_validation_status_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_last_validation_status_check
        CHECK (last_validation_status IS NULL OR last_validation_status IN ('success', 'failure'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS model_registry_global_model_id_unique_idx
    ON model_registry (global_model_id);

CREATE INDEX IF NOT EXISTS model_registry_lifecycle_lookup_idx
    ON model_registry (lifecycle_state, is_validation_current, last_validation_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS model_registry_task_hosting_idx
    ON model_registry (task_key, hosting_kind, runtime_mode_policy);

CREATE TABLE IF NOT EXISTS model_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL DEFAULT 'weights',
    storage_path TEXT NOT NULL,
    artifact_status TEXT NOT NULL DEFAULT 'ready',
    provenance TEXT,
    size_bytes BIGINT,
    checksum TEXT,
    runtime_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_id, artifact_type)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_artifacts_status_check'
    ) THEN
        ALTER TABLE model_artifacts
        ADD CONSTRAINT model_artifacts_status_check
        CHECK (artifact_status IN ('missing', 'staged', 'ready', 'corrupt'));
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS model_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    validator_kind TEXT NOT NULL,
    trigger_reason TEXT NOT NULL,
    result TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    error_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_fingerprint TEXT,
    validated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_validations_result_check'
    ) THEN
        ALTER TABLE model_validations
        ADD CONSTRAINT model_validations_result_check
        CHECK (result IN ('success', 'failure'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS model_validations_model_created_idx
    ON model_validations (model_id, created_at DESC);

CREATE TABLE IF NOT EXISTS model_runtime_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    dependency_kind TEXT NOT NULL,
    dependency_key TEXT NOT NULL,
    dependency_value TEXT,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_id, dependency_kind, dependency_key)
);

CREATE INDEX IF NOT EXISTS model_runtime_dependencies_model_idx
    ON model_runtime_dependencies (model_id, dependency_kind);

CREATE TABLE IF NOT EXISTS model_usage_daily (
    usage_date DATE NOT NULL,
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    metric_key TEXT NOT NULL,
    metric_value NUMERIC(18,3) NOT NULL DEFAULT 0,
    request_count BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (usage_date, model_id, user_id, metric_key)
);

CREATE INDEX IF NOT EXISTS model_usage_daily_model_idx
    ON model_usage_daily (model_id, usage_date DESC);

CREATE INDEX IF NOT EXISTS model_usage_daily_user_idx
    ON model_usage_daily (user_id, usage_date DESC);

INSERT INTO model_artifacts (
    model_id,
    artifact_type,
    storage_path,
    artifact_status,
    provenance,
    checksum,
    created_by_user_id
)
SELECT
    model_id,
    'weights',
    local_path,
    CASE
        WHEN COALESCE(status, 'available') = 'failed' THEN 'missing'
        WHEN COALESCE(status, 'available') = 'downloading' THEN 'staged'
        ELSE 'ready'
    END,
    source_id,
    checksum,
    COALESCE(owner_user_id, created_by_user_id)
FROM model_registry
WHERE COALESCE(local_path, '') <> ''
ON CONFLICT (model_id, artifact_type) DO NOTHING;

