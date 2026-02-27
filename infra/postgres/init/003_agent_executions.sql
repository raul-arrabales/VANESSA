CREATE TABLE IF NOT EXISTS agent_executions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    runtime_profile TEXT NOT NULL,
    requested_by_user_id BIGINT,
    input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_executions_agent_id_idx ON agent_executions (agent_id);
CREATE INDEX IF NOT EXISTS agent_executions_created_idx ON agent_executions (created_at DESC);
