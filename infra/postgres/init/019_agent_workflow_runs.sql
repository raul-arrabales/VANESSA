CREATE TABLE IF NOT EXISTS agent_workflow_runs (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assistant_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idle',
    workflow_execution_mode TEXT NOT NULL DEFAULT 'one_time',
    session_state TEXT NOT NULL DEFAULT 'active',
    workflow_cycle INTEGER NOT NULL DEFAULT 1,
    cycle_started_message_index INTEGER NOT NULL DEFAULT 0,
    workflow_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT agent_workflow_runs_status_check
        CHECK (status IN ('idle', 'awaiting_user_input', 'running', 'completed', 'failed')),
    CONSTRAINT agent_workflow_runs_execution_mode_check
        CHECK (workflow_execution_mode IN ('one_time', 'loop')),
    CONSTRAINT agent_workflow_runs_session_state_check
        CHECK (session_state IN ('active', 'closed')),
    CONSTRAINT agent_workflow_runs_conversation_assistant_unique
        UNIQUE (conversation_id, assistant_ref)
);

ALTER TABLE agent_workflow_runs
    ADD COLUMN IF NOT EXISTS workflow_execution_mode TEXT NOT NULL DEFAULT 'one_time',
    ADD COLUMN IF NOT EXISTS session_state TEXT NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS workflow_cycle INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS cycle_started_message_index INTEGER NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_workflow_runs_execution_mode_check'
    ) THEN
        ALTER TABLE agent_workflow_runs
        ADD CONSTRAINT agent_workflow_runs_execution_mode_check
        CHECK (workflow_execution_mode IN ('one_time', 'loop'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_workflow_runs_session_state_check'
    ) THEN
        ALTER TABLE agent_workflow_runs
        ADD CONSTRAINT agent_workflow_runs_session_state_check
        CHECK (session_state IN ('active', 'closed'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS agent_workflow_runs_owner_updated_idx
    ON agent_workflow_runs (owner_user_id, updated_at DESC);
