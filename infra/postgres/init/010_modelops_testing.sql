CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS model_test_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
    task_key TEXT NOT NULL,
    result TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms DOUBLE PRECISION,
    config_fingerprint TEXT,
    tested_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'model_test_runs_result_check'
    ) THEN
        ALTER TABLE model_test_runs
        ADD CONSTRAINT model_test_runs_result_check
        CHECK (result IN ('success', 'failure'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS model_test_runs_model_created_idx
    ON model_test_runs (model_id, created_at DESC);
