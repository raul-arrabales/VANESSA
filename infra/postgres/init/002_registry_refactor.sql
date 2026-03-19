-- Unified registry + governance schema additions.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS registry_entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('model', 'agent', 'tool')),
    owner_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    visibility TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('private', 'unlisted', 'public')),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived', 'available', 'downloading', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS registry_entities_type_idx ON registry_entities (entity_type, updated_at DESC);
CREATE INDEX IF NOT EXISTS registry_entities_owner_idx ON registry_entities (owner_user_id);

CREATE TABLE IF NOT EXISTS registry_versions (
    version_id UUID PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    spec_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_id, version)
);

CREATE INDEX IF NOT EXISTS registry_versions_entity_current_idx ON registry_versions (entity_id, is_current);

CREATE TABLE IF NOT EXISTS registry_labels (
    entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    label_key TEXT NOT NULL,
    label_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entity_id, label_key, label_value)
);

CREATE TABLE IF NOT EXISTS agent_bindings (
    agent_entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    model_entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    default_model_version TEXT,
    constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (agent_entity_id, model_entity_id)
);

CREATE TABLE IF NOT EXISTS agent_tool_bindings (
    agent_entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    tool_entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    tool_policy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (agent_entity_id, tool_entity_id)
);

CREATE TABLE IF NOT EXISTS entity_shares (
    entity_id TEXT NOT NULL REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    grantee_type TEXT NOT NULL CHECK (grantee_type IN ('user', 'group', 'org', 'public')),
    grantee_id TEXT NOT NULL DEFAULT '',
    permission TEXT NOT NULL CHECK (permission IN ('view', 'fork', 'execute', 'admin')),
    shared_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entity_id, grantee_type, grantee_id, permission)
);

CREATE TABLE IF NOT EXISTS policy_rules (
    id BIGSERIAL PRIMARY KEY,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    effect TEXT NOT NULL CHECK (effect IN ('allow', 'deny')),
    rule_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS policy_rules_scope_idx ON policy_rules (scope_type, scope_id);
CREATE INDEX IF NOT EXISTS policy_rules_resource_idx ON policy_rules (resource_type, resource_id);

CREATE TABLE IF NOT EXISTS system_runtime_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Compatibility mapping from legacy model_registry to unified registry entities.
DO $$
BEGIN
    IF to_regclass('public.model_registry') IS NOT NULL THEN
        INSERT INTO registry_entities (entity_id, entity_type, owner_user_id, visibility, status, created_at, updated_at)
        SELECT
            m.model_id,
            'model',
            m.created_by_user_id,
            'private',
            m.status,
            m.created_at,
            m.updated_at
        FROM model_registry m
        ON CONFLICT (entity_id) DO NOTHING;

        INSERT INTO registry_versions (version_id, entity_id, version, spec_json, is_current, published_at, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            m.model_id,
            'v1',
            jsonb_build_object(
                'name', m.name,
                'provider', m.provider,
                'source_id', m.source_id,
                'local_path', m.local_path,
                'metadata', COALESCE(m.metadata, '{}'::jsonb)
            ),
            TRUE,
            NOW(),
            m.created_at,
            m.updated_at
        FROM model_registry m
        WHERE NOT EXISTS (
            SELECT 1 FROM registry_versions rv WHERE rv.entity_id = m.model_id
        );
    END IF;
END
$$;
