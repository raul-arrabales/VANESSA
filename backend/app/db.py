from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


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
