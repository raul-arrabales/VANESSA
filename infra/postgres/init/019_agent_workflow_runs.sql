CREATE TABLE IF NOT EXISTS agent_workflow_runs (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assistant_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idle',
    workflow_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT agent_workflow_runs_status_check
        CHECK (status IN ('idle', 'awaiting_user_input', 'running', 'completed', 'failed')),
    CONSTRAINT agent_workflow_runs_conversation_assistant_unique
        UNIQUE (conversation_id, assistant_ref)
);

CREATE INDEX IF NOT EXISTS agent_workflow_runs_owner_updated_idx
    ON agent_workflow_runs (owner_user_id, updated_at DESC);
