CREATE TABLE IF NOT EXISTS quotes (
    id BIGSERIAL PRIMARY KEY,
    language TEXT NOT NULL,
    text TEXT NOT NULL,
    author TEXT NOT NULL,
    source_universe TEXT NOT NULL DEFAULT 'Original',
    tone TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    origin TEXT NOT NULL DEFAULT 'local',
    external_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'quotes_origin_check'
    ) THEN
        ALTER TABLE quotes
        ADD CONSTRAINT quotes_origin_check
        CHECK (origin IN ('local', 'cloud'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS quotes_language_text_unique_idx
    ON quotes (language, text);

CREATE INDEX IF NOT EXISTS quotes_lookup_idx
    ON quotes (language, is_active, is_approved);
