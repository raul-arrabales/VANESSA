ALTER TABLE agent_projects
    ADD COLUMN IF NOT EXISTS agent_type TEXT NOT NULL DEFAULT 'workflow',
    ADD COLUMN IF NOT EXISTS channel_type TEXT NOT NULL DEFAULT 'vanessa_webapp',
    ADD COLUMN IF NOT EXISTS interface_type TEXT NOT NULL DEFAULT 'chat',
    ADD COLUMN IF NOT EXISTS workflow_execution_mode TEXT NOT NULL DEFAULT 'one_time';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_projects_agent_type_check'
    ) THEN
        ALTER TABLE agent_projects
        ADD CONSTRAINT agent_projects_agent_type_check
        CHECK (agent_type IN ('workflow', 'planner', 'react'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_projects_channel_type_check'
    ) THEN
        ALTER TABLE agent_projects
        ADD CONSTRAINT agent_projects_channel_type_check
        CHECK (channel_type IN ('vanessa_webapp'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_projects_interface_type_check'
    ) THEN
        ALTER TABLE agent_projects
        ADD CONSTRAINT agent_projects_interface_type_check
        CHECK (interface_type IN ('chat'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agent_projects_workflow_execution_mode_check'
    ) THEN
        ALTER TABLE agent_projects
        ADD CONSTRAINT agent_projects_workflow_execution_mode_check
        CHECK (workflow_execution_mode IN ('one_time', 'loop'));
    END IF;
END
$$;
