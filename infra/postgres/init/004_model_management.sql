-- Workstream 1: model management + credential + assignment + immutable audit foundations.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS model_provider_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credential_scope TEXT NOT NULL CHECK (credential_scope IN ('platform', 'personal')),
    provider_slug TEXT NOT NULL,
    display_name TEXT NOT NULL,
    api_base_url TEXT,
    api_key_encrypted BYTEA NOT NULL,
    api_key_last4 TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (owner_user_id, provider_slug, display_name)
);

CREATE INDEX IF NOT EXISTS model_provider_credentials_owner_idx
    ON model_provider_credentials (owner_user_id, provider_slug, is_active);

ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS origin_scope TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS backend_kind TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS source_kind TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS availability TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS access_scope TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS provider_model_id TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS credential_id UUID REFERENCES model_provider_credentials(id) ON DELETE SET NULL;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS model_size_billion NUMERIC(10,3);
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS model_type TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS comment TEXT;
ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS registered_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;

UPDATE model_registry
SET
    origin_scope = COALESCE(origin_scope, 'platform'),
    backend_kind = COALESCE(backend_kind,
        CASE
            WHEN provider IN ('huggingface', 'local', 'vllm') OR local_path IS NOT NULL THEN 'local'
            ELSE 'external_api'
        END
    ),
    source_kind = COALESCE(source_kind,
        CASE
            WHEN provider = 'huggingface' THEN 'hf_import'
            WHEN local_path IS NOT NULL THEN 'local_folder'
            ELSE 'external_provider'
        END
    ),
    availability = COALESCE(availability,
        CASE
            WHEN provider IN ('huggingface', 'local', 'vllm') OR local_path IS NOT NULL THEN 'offline_ready'
            ELSE 'online_only'
        END
    ),
    access_scope = COALESCE(access_scope, 'assigned'),
    registered_by_user_id = COALESCE(registered_by_user_id, created_by_user_id)
WHERE
    origin_scope IS NULL
    OR backend_kind IS NULL
    OR source_kind IS NULL
    OR availability IS NULL
    OR access_scope IS NULL
    OR registered_by_user_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_origin_scope_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_origin_scope_check
        CHECK (origin_scope IN ('platform', 'personal'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_backend_kind_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_backend_kind_check
        CHECK (backend_kind IN ('local', 'external_api'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_source_kind_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_source_kind_check
        CHECK (source_kind IN ('hf_import', 'local_folder', 'external_provider'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_availability_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_availability_check
        CHECK (availability IN ('online_only', 'offline_ready'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_registry_access_scope_check'
    ) THEN
        ALTER TABLE model_registry
        ADD CONSTRAINT model_registry_access_scope_check
        CHECK (access_scope IN ('private', 'assigned', 'global'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS model_registry_origin_access_idx
    ON model_registry (origin_scope, access_scope, availability, updated_at DESC);
CREATE INDEX IF NOT EXISTS model_registry_credential_idx
    ON model_registry (credential_id);

CREATE TABLE IF NOT EXISTS user_groups (
    id BIGSERIAL PRIMARY KEY,
    group_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_group_memberships (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    added_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS model_user_assignments (
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (model_id, user_id)
);

CREATE TABLE IF NOT EXISTS model_group_assignments (
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    assigned_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (model_id, group_id)
);

CREATE TABLE IF NOT EXISTS model_global_assignments (
    model_id TEXT PRIMARY KEY REFERENCES model_registry(model_id) ON DELETE CASCADE,
    assigned_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_default_preferences (
    id BIGSERIAL PRIMARY KEY,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('user', 'workspace')),
    scope_key TEXT NOT NULL,
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 100,
    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (scope_type, scope_key)
);

CREATE INDEX IF NOT EXISTS model_default_preferences_resolve_idx
    ON model_default_preferences (scope_type, scope_key, priority ASC);

CREATE TABLE IF NOT EXISTS model_audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    actor_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_event_hash BYTEA,
    event_hash BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS model_audit_log_target_idx
    ON model_audit_log (target_type, target_id, created_at DESC);
CREATE INDEX IF NOT EXISTS model_audit_log_actor_idx
    ON model_audit_log (actor_user_id, created_at DESC);

CREATE OR REPLACE FUNCTION model_audit_log_set_hashes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    prior_hash BYTEA;
BEGIN
    SELECT event_hash
    INTO prior_hash
    FROM model_audit_log
    ORDER BY id DESC
    LIMIT 1;

    NEW.previous_event_hash := prior_hash;
    NEW.event_hash := digest(
        concat_ws(
            '|',
            COALESCE(NEW.event_id::TEXT, ''),
            COALESCE(NEW.actor_user_id::TEXT, ''),
            COALESCE(NEW.event_type, ''),
            COALESCE(NEW.target_type, ''),
            COALESCE(NEW.target_id, ''),
            COALESCE(NEW.payload::TEXT, ''),
            COALESCE(encode(prior_hash, 'hex'), ''),
            COALESCE(NEW.created_at::TEXT, '')
        ),
        'sha256'
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS model_audit_log_set_hashes_trigger ON model_audit_log;
CREATE TRIGGER model_audit_log_set_hashes_trigger
BEFORE INSERT ON model_audit_log
FOR EACH ROW
EXECUTE FUNCTION model_audit_log_set_hashes();

CREATE OR REPLACE FUNCTION model_audit_log_prevent_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'model_audit_log is immutable';
END;
$$;

DROP TRIGGER IF EXISTS model_audit_log_no_update_trigger ON model_audit_log;
CREATE TRIGGER model_audit_log_no_update_trigger
BEFORE UPDATE ON model_audit_log
FOR EACH ROW
EXECUTE FUNCTION model_audit_log_prevent_mutation();

DROP TRIGGER IF EXISTS model_audit_log_no_delete_trigger ON model_audit_log;
CREATE TRIGGER model_audit_log_no_delete_trigger
BEFORE DELETE ON model_audit_log
FOR EACH ROW
EXECUTE FUNCTION model_audit_log_prevent_mutation();
