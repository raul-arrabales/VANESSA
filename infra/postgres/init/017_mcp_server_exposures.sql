-- Separate internal tool definitions from MCP Gateway exposure wrappers.
ALTER TABLE registry_entities
    DROP CONSTRAINT IF EXISTS registry_entities_entity_type_check;

ALTER TABLE registry_entities
    ADD CONSTRAINT registry_entities_entity_type_check
    CHECK (entity_type IN ('model', 'agent', 'tool', 'mcp_server'));

CREATE TABLE IF NOT EXISTS catalog_tool_runtime_status (
    tool_id TEXT PRIMARY KEY REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    validated_version TEXT,
    last_validation_status TEXT NOT NULL DEFAULT 'unknown',
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalog_mcp_server_status (
    mcp_server_id TEXT PRIMARY KEY REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
    validated_version TEXT,
    runtime_status TEXT NOT NULL DEFAULT 'unknown',
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mcp_invocation_audit_log (
    id BIGSERIAL PRIMARY KEY,
    mcp_server_id TEXT REFERENCES registry_entities(entity_id) ON DELETE SET NULL,
    mcp_server_slug TEXT NOT NULL,
    backing_tool_id TEXT REFERENCES registry_entities(entity_id) ON DELETE SET NULL,
    agent_id TEXT,
    agent_domain TEXT,
    delegated_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    delegated_user_role TEXT,
    status TEXT NOT NULL,
    status_code INTEGER,
    error_json JSONB,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    request_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS mcp_invocation_audit_created_idx
    ON mcp_invocation_audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS mcp_invocation_audit_server_idx
    ON mcp_invocation_audit_log (mcp_server_slug, created_at DESC);

ALTER TABLE agent_projects
    ADD COLUMN IF NOT EXISTS mcp_server_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS agent_domain TEXT NOT NULL DEFAULT 'default';

DO $$
DECLARE
    tool_row RECORD;
    agent_row RECORD;
    current_spec JSONB;
    next_version TEXT;
    exposed_slug TEXT;
    mcp_id TEXT;
    mcp_spec JSONB;
    new_tool_refs JSONB;
    new_mcp_refs JSONB;
BEGIN
    FOR tool_row IN
        SELECT e.entity_id, e.owner_user_id, v.version, v.spec_json, v.published_at
        FROM registry_entities e
        JOIN registry_versions v
          ON v.entity_id = e.entity_id AND v.is_current = TRUE
        WHERE e.entity_type = 'tool'
          AND v.spec_json ? 'transport'
    LOOP
        current_spec := tool_row.spec_json;

        IF current_spec->>'transport' = 'mcp' THEN
            exposed_slug := regexp_replace(coalesce(current_spec->>'tool_name', tool_row.entity_id), '[^a-zA-Z0-9_.-]+', '-', 'g');
            mcp_id := 'mcp.' || exposed_slug;
            mcp_spec := jsonb_build_object(
                'name', current_spec->>'name',
                'slug', exposed_slug,
                'description', coalesce(current_spec->>'description', ''),
                'backing_tool_id', tool_row.entity_id,
                'exposed_tool_name', coalesce(current_spec->>'tool_name', exposed_slug),
                'input_schema', coalesce(current_spec->'input_schema', '{}'::jsonb),
                'output_schema', coalesce(current_spec->'output_schema', '{}'::jsonb),
                'metadata', jsonb_build_object(
                    'category', 'custom',
                    'capabilities', '[]'::jsonb,
                    'local', coalesce((current_spec->>'offline_compatible')::boolean, false),
                    'stateless', true,
                    'sandboxed', false,
                    'risk_level', 'medium',
                    'data_access', 'none',
                    'output_freshness', 'runtime_generated',
                    'audit_level', 'standard'
                ),
                'authorization_policy', jsonb_build_object(
                    'agent_ids', jsonb_build_array('*'),
                    'agent_domains', jsonb_build_array('*'),
                    'agent_roles', jsonb_build_array('*'),
                    'user_roles', jsonb_build_array('*'),
                    'user_ids', jsonb_build_array('*'),
                    'user_group_ids', jsonb_build_array('*')
                ),
                'enabled', true
            );

            INSERT INTO registry_entities (entity_id, entity_type, owner_user_id, visibility, status)
            VALUES (mcp_id, 'mcp_server', tool_row.owner_user_id, 'private', 'published')
            ON CONFLICT (entity_id) DO NOTHING;

            IF NOT EXISTS (SELECT 1 FROM registry_versions WHERE entity_id = mcp_id AND version = 'v1') THEN
                INSERT INTO registry_versions (version_id, entity_id, version, spec_json, is_current, published_at)
                VALUES (gen_random_uuid(), mcp_id, 'v1', mcp_spec, TRUE, NOW());
            END IF;

            INSERT INTO catalog_mcp_server_status (
                mcp_server_id,
                validated_version,
                runtime_status,
                validation_errors,
                last_validated_at
            )
            VALUES (mcp_id, 'v1', 'success', '[]'::jsonb, NOW())
            ON CONFLICT (mcp_server_id) DO NOTHING;
        END IF;

        next_version := 'v' || (
            SELECT COALESCE(MAX(NULLIF(regexp_replace(version, '\D', '', 'g'), '')::INTEGER), 1) + 1
            FROM registry_versions
            WHERE entity_id = tool_row.entity_id
        );

        UPDATE registry_versions
        SET is_current = FALSE
        WHERE entity_id = tool_row.entity_id;

        INSERT INTO registry_versions (version_id, entity_id, version, spec_json, is_current, published_at)
        VALUES (
            gen_random_uuid(),
            tool_row.entity_id,
            next_version,
            (current_spec - 'transport' - 'connection_profile_ref' - 'tool_name')
                || jsonb_build_object(
                    'execution_backend',
                    CASE current_spec->>'transport'
                        WHEN 'sandbox_http' THEN 'sandbox_python'
                        WHEN 'mcp' THEN 'web_search'
                        ELSE 'internal_http'
                    END,
                    'execution_config',
                    CASE current_spec->>'transport'
                        WHEN 'mcp' THEN jsonb_build_object('provider_tool_name', coalesce(current_spec->>'tool_name', 'web_search'))
                        ELSE '{}'::jsonb
                    END,
                    'permissions', '{}'::jsonb
                ),
            TRUE,
            tool_row.published_at
        );

        INSERT INTO catalog_tool_runtime_status (
            tool_id,
            validated_version,
            last_validation_status,
            validation_errors,
            last_validated_at
        )
        VALUES (tool_row.entity_id, next_version, 'success', '[]'::jsonb, NOW())
        ON CONFLICT (tool_id)
        DO UPDATE SET
            validated_version = EXCLUDED.validated_version,
            last_validation_status = EXCLUDED.last_validation_status,
            validation_errors = EXCLUDED.validation_errors,
            last_validated_at = NOW(),
            updated_at = NOW();
    END LOOP;

    FOR agent_row IN
        SELECT e.entity_id, v.spec_json
        FROM registry_entities e
        JOIN registry_versions v
          ON v.entity_id = e.entity_id AND v.is_current = TRUE
        WHERE e.entity_type = 'agent'
    LOOP
        current_spec := agent_row.spec_json;
        new_tool_refs := '[]'::jsonb;
        new_mcp_refs := coalesce(current_spec->'mcp_server_refs', '[]'::jsonb);

        SELECT coalesce(jsonb_agg(value), '[]'::jsonb)
        INTO new_tool_refs
        FROM jsonb_array_elements_text(coalesce(current_spec->'tool_refs', '[]'::jsonb)) AS refs(value)
        WHERE NOT EXISTS (
            SELECT 1
            FROM registry_entities e
            JOIN registry_versions v
              ON v.entity_id = e.entity_id AND v.is_current = TRUE
            WHERE e.entity_type = 'mcp_server'
              AND v.spec_json->>'backing_tool_id' = refs.value
        );

        SELECT coalesce(new_mcp_refs || jsonb_agg(v.spec_json->>'slug'), new_mcp_refs)
        INTO new_mcp_refs
        FROM jsonb_array_elements_text(coalesce(current_spec->'tool_refs', '[]'::jsonb)) AS refs(value)
        JOIN registry_entities e
          ON e.entity_type = 'mcp_server'
        JOIN registry_versions v
          ON v.entity_id = e.entity_id AND v.is_current = TRUE
        WHERE v.spec_json->>'backing_tool_id' = refs.value;

        IF current_spec->'tool_refs' IS DISTINCT FROM new_tool_refs
           OR current_spec->'mcp_server_refs' IS DISTINCT FROM new_mcp_refs
           OR coalesce(current_spec->>'agent_domain', '') = '' THEN
            next_version := 'v' || (
                SELECT COALESCE(MAX(NULLIF(regexp_replace(version, '\D', '', 'g'), '')::INTEGER), 1) + 1
                FROM registry_versions
                WHERE entity_id = agent_row.entity_id
            );

            UPDATE registry_versions
            SET is_current = FALSE
            WHERE entity_id = agent_row.entity_id;

            INSERT INTO registry_versions (version_id, entity_id, version, spec_json, is_current, published_at)
            SELECT
                gen_random_uuid(),
                agent_row.entity_id,
                next_version,
                (current_spec || jsonb_build_object(
                    'tool_refs', new_tool_refs,
                    'mcp_server_refs', new_mcp_refs,
                    'agent_domain', coalesce(current_spec->>'agent_domain', 'default')
                )),
                TRUE,
                published_at
            FROM registry_versions
            WHERE entity_id = agent_row.entity_id
            ORDER BY created_at DESC
            LIMIT 1;
        END IF;
    END LOOP;
END
$$;
