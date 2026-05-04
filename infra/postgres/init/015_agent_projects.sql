CREATE TABLE IF NOT EXISTS agent_projects (
    id TEXT PRIMARY KEY,
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    instructions TEXT NOT NULL,
    runtime_prompts JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_model_ref TEXT,
    tool_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    workflow_definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    runtime_constraints JSONB NOT NULL DEFAULT '{"internet_required": false, "sandbox_required": false}'::jsonb,
    visibility TEXT NOT NULL DEFAULT 'private',
    published_agent_id TEXT,
    current_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_projects_visibility_check'
    ) THEN
        ALTER TABLE agent_projects
        ADD CONSTRAINT agent_projects_visibility_check
        CHECK (visibility IN ('private', 'unlisted', 'public'));
    END IF;
END
$$;

ALTER TABLE agent_projects
    ADD COLUMN IF NOT EXISTS runtime_prompts JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS agent_project_versions (
    project_id TEXT NOT NULL REFERENCES agent_projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    spec_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, version)
);

CREATE INDEX IF NOT EXISTS agent_projects_owner_updated_idx
    ON agent_projects (owner_user_id, updated_at DESC);
