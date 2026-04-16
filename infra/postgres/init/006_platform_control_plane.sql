CREATE TABLE IF NOT EXISTS platform_capabilities (
    capability_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_provider_families (
    provider_key TEXT PRIMARY KEY,
    capability_key TEXT NOT NULL REFERENCES platform_capabilities(capability_key) ON DELETE CASCADE,
    adapter_kind TEXT NOT NULL,
    provider_origin TEXT NOT NULL DEFAULT 'local',
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT platform_provider_families_provider_origin_check CHECK (provider_origin IN ('local', 'cloud'))
);

ALTER TABLE platform_provider_families
    ADD COLUMN IF NOT EXISTS provider_origin TEXT NOT NULL DEFAULT 'local';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'platform_provider_families_provider_origin_check'
    ) THEN
        ALTER TABLE platform_provider_families
            ADD CONSTRAINT platform_provider_families_provider_origin_check
            CHECK (provider_origin IN ('local', 'cloud'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS platform_provider_families_capability_idx
    ON platform_provider_families (capability_key);

CREATE TABLE IF NOT EXISTS platform_provider_instances (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    provider_key TEXT NOT NULL REFERENCES platform_provider_families(provider_key) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    endpoint_url TEXT NOT NULL,
    healthcheck_url TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS platform_provider_instances_provider_idx
    ON platform_provider_instances (provider_key, enabled);

CREATE TABLE IF NOT EXISTS platform_deployment_profiles (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_deployment_bindings (
    id UUID PRIMARY KEY,
    deployment_profile_id UUID NOT NULL REFERENCES platform_deployment_profiles(id) ON DELETE CASCADE,
    capability_key TEXT NOT NULL REFERENCES platform_capabilities(capability_key) ON DELETE CASCADE,
    provider_instance_id UUID NOT NULL REFERENCES platform_provider_instances(id) ON DELETE RESTRICT,
    binding_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    resource_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (deployment_profile_id, capability_key)
);

ALTER TABLE platform_deployment_bindings
    DROP COLUMN IF EXISTS served_model_id;

CREATE TABLE IF NOT EXISTS platform_binding_resources (
    binding_id UUID NOT NULL REFERENCES platform_deployment_bindings(id) ON DELETE CASCADE,
    resource_id TEXT NOT NULL,
    resource_kind TEXT NOT NULL,
    ref_type TEXT NOT NULL,
    managed_model_id TEXT REFERENCES model_registry(model_id) ON DELETE RESTRICT,
    provider_resource_id TEXT,
    display_name TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (binding_id, resource_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS platform_binding_resources_default_idx
    ON platform_binding_resources (binding_id)
    WHERE is_default = TRUE;

CREATE INDEX IF NOT EXISTS platform_deployment_bindings_profile_idx
    ON platform_deployment_bindings (deployment_profile_id);

CREATE INDEX IF NOT EXISTS platform_deployment_bindings_provider_idx
    ON platform_deployment_bindings (provider_instance_id);

CREATE INDEX IF NOT EXISTS platform_binding_resources_managed_model_idx
    ON platform_binding_resources (managed_model_id);

CREATE TABLE IF NOT EXISTS platform_active_deployment (
    singleton_key TEXT PRIMARY KEY,
    deployment_profile_id UUID NOT NULL REFERENCES platform_deployment_profiles(id) ON DELETE RESTRICT,
    previous_deployment_profile_id UUID REFERENCES platform_deployment_profiles(id) ON DELETE SET NULL,
    activated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_deployment_activation_audit (
    id UUID PRIMARY KEY,
    deployment_profile_id UUID NOT NULL REFERENCES platform_deployment_profiles(id) ON DELETE CASCADE,
    previous_deployment_profile_id UUID REFERENCES platform_deployment_profiles(id) ON DELETE SET NULL,
    activated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS platform_activation_audit_profile_idx
    ON platform_deployment_activation_audit (deployment_profile_id, activated_at DESC);
