from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from ..db import get_connection


def ensure_catalog_runtime_tables(database_url: str) -> None:
    with get_connection(database_url) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_tool_runtime_status (
                tool_id TEXT PRIMARY KEY REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
                validated_version TEXT,
                last_validation_status TEXT NOT NULL DEFAULT 'unknown',
                validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
                last_validated_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_mcp_server_status (
                mcp_server_id TEXT PRIMARY KEY REFERENCES registry_entities(entity_id) ON DELETE CASCADE,
                validated_version TEXT,
                runtime_status TEXT NOT NULL DEFAULT 'unknown',
                validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
                last_validated_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_invocation_audit_log (
                id BIGSERIAL PRIMARY KEY,
                mcp_server_id TEXT REFERENCES registry_entities(entity_id) ON DELETE SET NULL,
                mcp_server_slug TEXT NOT NULL,
                backing_tool_id TEXT REFERENCES registry_entities(entity_id) ON DELETE SET NULL,
                agent_id TEXT,
                agent_domain TEXT,
                delegated_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                delegated_user_role TEXT,
                status TEXT NOT NULL,
                status_code INTEGER,
                error_json JSONB,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                request_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def list_tool_runtime_statuses(database_url: str) -> dict[str, dict[str, Any]]:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        rows = connection.execute("SELECT * FROM catalog_tool_runtime_status").fetchall()
    return {str(row["tool_id"]): dict(row) for row in rows}


def get_tool_runtime_status(database_url: str, *, tool_id: str) -> dict[str, Any] | None:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT * FROM catalog_tool_runtime_status WHERE tool_id = %s",
            (tool_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def upsert_tool_runtime_status(
    database_url: str,
    *,
    tool_id: str,
    validated_version: str,
    last_validation_status: str,
    validation_errors: list[str],
) -> dict[str, Any]:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO catalog_tool_runtime_status (
                tool_id,
                validated_version,
                last_validation_status,
                validation_errors,
                last_validated_at
            )
            VALUES (%s, %s, %s, %s::jsonb, NOW())
            ON CONFLICT (tool_id)
            DO UPDATE SET
                validated_version = EXCLUDED.validated_version,
                last_validation_status = EXCLUDED.last_validation_status,
                validation_errors = EXCLUDED.validation_errors,
                last_validated_at = NOW(),
                updated_at = NOW()
            RETURNING *
            """,
            (
                tool_id.strip(),
                validated_version.strip(),
                last_validation_status.strip().lower(),
                Jsonb(validation_errors),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_update_tool_runtime_status")
    return dict(row)


def list_mcp_server_statuses(database_url: str) -> dict[str, dict[str, Any]]:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        rows = connection.execute("SELECT * FROM catalog_mcp_server_status").fetchall()
    return {str(row["mcp_server_id"]): dict(row) for row in rows}


def get_mcp_server_status(database_url: str, *, mcp_server_id: str) -> dict[str, Any] | None:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT * FROM catalog_mcp_server_status WHERE mcp_server_id = %s",
            (mcp_server_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def upsert_mcp_server_status(
    database_url: str,
    *,
    mcp_server_id: str,
    validated_version: str,
    runtime_status: str,
    validation_errors: list[str],
) -> dict[str, Any]:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO catalog_mcp_server_status (
                mcp_server_id,
                validated_version,
                runtime_status,
                validation_errors,
                last_validated_at
            )
            VALUES (%s, %s, %s, %s::jsonb, NOW())
            ON CONFLICT (mcp_server_id)
            DO UPDATE SET
                validated_version = EXCLUDED.validated_version,
                runtime_status = EXCLUDED.runtime_status,
                validation_errors = EXCLUDED.validation_errors,
                last_validated_at = NOW(),
                updated_at = NOW()
            RETURNING *
            """,
            (
                mcp_server_id.strip(),
                validated_version.strip(),
                runtime_status.strip().lower(),
                Jsonb(validation_errors),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_update_mcp_server_status")
    return dict(row)


def list_user_group_ids(database_url: str, *, user_id: int) -> set[str]:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        rows = connection.execute(
            "SELECT group_id FROM user_group_memberships WHERE user_id = %s",
            (user_id,),
        ).fetchall()
    return {str(row["group_id"]) for row in rows}


def log_mcp_invocation(
    database_url: str,
    *,
    mcp_server_id: str | None,
    mcp_server_slug: str,
    backing_tool_id: str | None,
    agent_id: str | None,
    agent_domain: str | None,
    delegated_user_id: int | None,
    delegated_user_role: str | None,
    status: str,
    status_code: int | None,
    error: dict[str, Any] | None,
    duration_ms: int,
    request_metadata: dict[str, Any],
) -> dict[str, Any]:
    ensure_catalog_runtime_tables(database_url)
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO mcp_invocation_audit_log (
                mcp_server_id,
                mcp_server_slug,
                backing_tool_id,
                agent_id,
                agent_domain,
                delegated_user_id,
                delegated_user_role,
                status,
                status_code,
                error_json,
                duration_ms,
                request_metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
            RETURNING *
            """,
            (
                mcp_server_id,
                mcp_server_slug,
                backing_tool_id,
                agent_id,
                agent_domain,
                delegated_user_id,
                delegated_user_role,
                status,
                status_code,
                Jsonb(error) if error is not None else None,
                duration_ms,
                Jsonb(request_metadata),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_log_mcp_invocation")
    return dict(row)
