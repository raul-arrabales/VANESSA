from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from .quote_seed_data import build_quote_seed_rows


@contextmanager
def get_connection(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        yield connection


def run_auth_schema_migration(database_url: str) -> None:
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT")
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )

            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'users_role_check'
                    ) THEN
                        ALTER TABLE users
                        ADD CONSTRAINT users_role_check
                        CHECK (role IN ('superadmin', 'admin', 'user'));
                    END IF;
                END
                $$
                """
            )

            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique_idx ON users (email)"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS users_username_unique_idx ON users (username)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_registry (
                    id BIGSERIAL PRIMARY KEY,
                    model_id TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    provider_config_ref TEXT,
                    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS model_id TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS provider TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS provider_config_ref TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS name TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS source_id TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS local_path TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_registry ADD COLUMN IF NOT EXISTS status TEXT"
            )
            cursor.execute(
                """
                UPDATE model_registry
                SET
                    name = COALESCE(name, NULLIF(metadata->>'name', ''), model_id),
                    source_id = COALESCE(source_id, NULLIF(metadata->>'source_id', '')),
                    local_path = COALESCE(local_path, NULLIF(metadata->>'local_path', '')),
                    status = COALESCE(status, NULLIF(metadata->>'status', ''), 'available')
                """
            )
            cursor.execute(
                "ALTER TABLE model_registry ALTER COLUMN name SET NOT NULL"
            )
            cursor.execute(
                "ALTER TABLE model_registry ALTER COLUMN status SET DEFAULT 'available'"
            )
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'model_registry_status_check'
                    ) THEN
                        ALTER TABLE model_registry
                        ADD CONSTRAINT model_registry_status_check
                        CHECK (status IN ('available', 'downloading', 'failed', 'archived'));
                    END IF;
                END
                $$
                """
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS model_registry_model_id_unique_idx ON model_registry (model_id)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_access_assignments (
                    id BIGSERIAL PRIMARY KEY,
                    model_id TEXT NOT NULL REFERENCES model_registry(model_id) ON DELETE CASCADE,
                    scope_type TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    assigned_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(model_id, scope_type, scope_id)
                )
                """
            )
            cursor.execute(
                "ALTER TABLE model_access_assignments ADD COLUMN IF NOT EXISTS model_id TEXT REFERENCES model_registry(model_id) ON DELETE CASCADE"
            )
            cursor.execute(
                "ALTER TABLE model_access_assignments ADD COLUMN IF NOT EXISTS scope_type TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_access_assignments ADD COLUMN IF NOT EXISTS scope_id TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_access_assignments ADD COLUMN IF NOT EXISTS assigned_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            cursor.execute(
                "ALTER TABLE model_access_assignments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE model_access_assignments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS model_access_assignments_scope_idx ON model_access_assignments (scope_type, scope_id)"
            )
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'model_access_assignments_scope_type_check'
                    ) THEN
                        ALTER TABLE model_access_assignments
                        ADD CONSTRAINT model_access_assignments_scope_type_check
                        CHECK (scope_type IN ('org', 'group', 'user'));
                    END IF;
                END
                $$
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_scope_assignments (
                    id BIGSERIAL PRIMARY KEY,
                    scope TEXT NOT NULL,
                    model_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(scope)
                )
                """
            )
            cursor.execute(
                "ALTER TABLE model_scope_assignments ADD COLUMN IF NOT EXISTS scope TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_scope_assignments ADD COLUMN IF NOT EXISTS model_ids JSONB NOT NULL DEFAULT '[]'::jsonb"
            )
            cursor.execute(
                "ALTER TABLE model_scope_assignments ADD COLUMN IF NOT EXISTS updated_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            cursor.execute(
                "ALTER TABLE model_scope_assignments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE model_scope_assignments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'model_scope_assignments_scope_check'
                    ) THEN
                        ALTER TABLE model_scope_assignments
                        ADD CONSTRAINT model_scope_assignments_scope_check
                        CHECK (scope IN ('user', 'admin', 'superadmin'));
                    END IF;
                END
                $$
                """
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS model_scope_assignments_scope_unique_idx ON model_scope_assignments (scope)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_download_jobs (
                    id UUID PRIMARY KEY,
                    provider TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_dir TEXT NOT NULL,
                    model_id TEXT REFERENCES model_registry(model_id) ON DELETE SET NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    started_at TIMESTAMPTZ,
                    finished_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS provider TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS source_id TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS target_dir TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS model_id TEXT REFERENCES model_registry(model_id) ON DELETE SET NULL"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS status TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS error_message TEXT"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE model_download_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'model_download_jobs_status_check'
                    ) THEN
                        ALTER TABLE model_download_jobs
                        ADD CONSTRAINT model_download_jobs_status_check
                        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled'));
                    END IF;
                END
                $$
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS model_download_jobs_status_created_idx ON model_download_jobs (status, created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS model_download_jobs_source_id_idx ON model_download_jobs (source_id)"
            )

    run_registry_schema_migration(database_url)
    run_model_management_schema_migration(database_url)
    run_platform_control_plane_schema_migration(database_url)
    run_quotes_schema_migration(database_url)
    run_chat_conversations_schema_migration(database_url)


def run_registry_schema_migration(database_url: str) -> None:
    migration_file = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "postgres"
        / "init"
        / "002_registry_refactor.sql"
    )
    migration_sql = migration_file.read_text(encoding="utf-8")

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(migration_sql)


def run_model_management_schema_migration(database_url: str) -> None:
    migration_file = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "postgres"
        / "init"
        / "004_model_management.sql"
    )
    migration_sql = migration_file.read_text(encoding="utf-8")

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(migration_sql)


def run_platform_control_plane_schema_migration(database_url: str) -> None:
    migration_file = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "postgres"
        / "init"
        / "006_platform_control_plane.sql"
    )
    migration_sql = migration_file.read_text(encoding="utf-8")

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(migration_sql)


def run_quotes_schema_migration(database_url: str) -> None:
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
                )
                """
            )
            cursor.execute("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS language TEXT")
            cursor.execute("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS text TEXT")
            cursor.execute("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS author TEXT")
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS source_universe TEXT NOT NULL DEFAULT 'Original'"
            )
            cursor.execute("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS tone TEXT")
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb"
            )
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"
            )
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT TRUE"
            )
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'local'"
            )
            cursor.execute("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS external_ref TEXT")
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
            cursor.execute(
                """
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
                $$
                """
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS quotes_language_text_unique_idx ON quotes (language, text)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS quotes_lookup_idx ON quotes (language, is_active, is_approved)"
            )

            quote_rows = build_quote_seed_rows()
            for row in quote_rows:
                cursor.execute(
                    """
                    INSERT INTO quotes (
                        language,
                        text,
                        author,
                        source_universe,
                        tone,
                        tags,
                        is_active,
                        is_approved,
                        origin,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, TRUE, TRUE, %s, %s, %s)
                    ON CONFLICT (language, text) DO NOTHING
                    """,
                    (
                        row["language"],
                        row["text"],
                        row["author"],
                        row["source_universe"],
                        row["tone"],
                        psycopg.types.json.Jsonb(row["tags"]),
                        row["origin"],
                        row["created_at"],
                        row["updated_at"],
                    ),
                )


def run_chat_conversations_schema_migration(database_url: str) -> None:
    migration_file = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "postgres"
        / "init"
        / "007_chat_conversations.sql"
    )
    migration_sql = migration_file.read_text(encoding="utf-8")

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(migration_sql)
