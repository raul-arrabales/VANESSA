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

INSERT INTO quotes (
    language,
    text,
    author,
    source_universe,
    tone,
    tags,
    is_active,
    is_approved,
    origin
)
VALUES
    (
        'en',
        'I asked the ship AI for meaning. It suggested a firmware update and a long walk among the stars.',
        'VANESSA Curated',
        'Original',
        'reflective',
        '["ai", "philosophy", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'en',
        'A wise captain debugs the console before blaming the galaxy.',
        'VANESSA Curated',
        'Original',
        'funny',
        '["ai", "funny", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'en',
        'Synthetic minds count possibilities. Sentient minds decide which ones deserve mercy.',
        'VANESSA Curated',
        'Original',
        'reflective',
        '["ai", "philosophy", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'en',
        'On a starship, even existential dread sounds better with clean telemetry.',
        'VANESSA Curated',
        'Original',
        'funny',
        '["funny", "philosophy", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'es',
        'Le pedi sentido a la IA de la nave. Me propuso una actualizacion de firmware y un paseo entre las estrellas.',
        'VANESSA Curated',
        'Original',
        'reflective',
        '["ai", "philosophy", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'es',
        'Una capitana sabia depura la consola antes de culpar a la galaxia.',
        'VANESSA Curated',
        'Original',
        'funny',
        '["ai", "funny", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'es',
        'Las mentes sinteticas cuentan posibilidades. Las conscientes eligen cuales merecen compasion.',
        'VANESSA Curated',
        'Original',
        'reflective',
        '["ai", "philosophy", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    ),
    (
        'es',
        'En una nave estelar, hasta la crisis existencial suena mejor con telemetria limpia.',
        'VANESSA Curated',
        'Original',
        'funny',
        '["funny", "philosophy", "scifi"]'::jsonb,
        TRUE,
        TRUE,
        'local'
    )
ON CONFLICT (language, text) DO NOTHING;
