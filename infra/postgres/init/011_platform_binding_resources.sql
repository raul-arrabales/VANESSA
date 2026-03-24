ALTER TABLE platform_deployment_bindings
    ADD COLUMN IF NOT EXISTS resource_policy JSONB NOT NULL DEFAULT '{}'::jsonb;

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

INSERT INTO platform_binding_resources (
    binding_id,
    resource_id,
    resource_kind,
    ref_type,
    managed_model_id,
    provider_resource_id,
    display_name,
    metadata_json,
    is_default,
    sort_order
)
SELECT
    bsm.binding_id,
    bsm.model_id,
    'model',
    'managed_model',
    bsm.model_id,
    COALESCE(NULLIF(m.provider_model_id, ''), NULLIF(m.local_path, '')),
    NULLIF(m.name, ''),
    jsonb_strip_nulls(
        jsonb_build_object(
            'provider', NULLIF(m.provider, ''),
            'backend', NULLIF(m.backend_kind, ''),
            'task_key', NULLIF(m.task_key, ''),
            'provider_model_id', NULLIF(m.provider_model_id, ''),
            'local_path', NULLIF(m.local_path, ''),
            'source_id', NULLIF(m.source_id, ''),
            'availability', NULLIF(m.availability, '')
        )
    ),
    bsm.is_default,
    bsm.sort_order
FROM platform_binding_served_models bsm
JOIN model_registry m ON m.model_id = bsm.model_id
ON CONFLICT (binding_id, resource_id) DO NOTHING;

CREATE UNIQUE INDEX IF NOT EXISTS platform_binding_resources_default_idx
    ON platform_binding_resources (binding_id)
    WHERE is_default = TRUE;

CREATE INDEX IF NOT EXISTS platform_binding_resources_managed_model_idx
    ON platform_binding_resources (managed_model_id);

DROP TABLE IF EXISTS platform_binding_served_models;
