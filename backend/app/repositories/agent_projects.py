from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import psycopg

from ..db import get_connection


def list_agent_projects(database_url: str, *, owner_user_id: int | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT
            p.id,
            p.owner_user_id,
            p.name,
            p.description,
            p.instructions,
            p.default_model_ref,
            p.tool_refs,
            p.workflow_definition,
            p.tool_policy,
            p.runtime_constraints,
            p.visibility,
            p.published_agent_id,
            p.current_version,
            p.created_at,
            p.updated_at
        FROM agent_projects AS p
    """
    params: list[object] = []
    if owner_user_id is not None:
        query += " WHERE p.owner_user_id = %s"
        params.append(owner_user_id)
    query += " ORDER BY p.updated_at DESC, p.created_at DESC, p.id ASC"
    with get_connection(database_url) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def get_agent_project(database_url: str, *, project_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                p.id,
                p.owner_user_id,
                p.name,
                p.description,
                p.instructions,
                p.default_model_ref,
                p.tool_refs,
                p.workflow_definition,
                p.tool_policy,
                p.runtime_constraints,
                p.visibility,
                p.published_agent_id,
                p.current_version,
                p.created_at,
                p.updated_at
            FROM agent_projects AS p
            WHERE p.id = %s
            """,
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


def create_agent_project(
    database_url: str,
    *,
    project_id: str,
    owner_user_id: int,
    spec: dict[str, Any],
    visibility: str,
) -> dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agent_projects (
                    id,
                    owner_user_id,
                    name,
                    description,
                    instructions,
                    default_model_ref,
                    tool_refs,
                    workflow_definition,
                    tool_policy,
                    runtime_constraints,
                    visibility,
                    published_agent_id,
                    current_version,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, NULL, 1, %s, %s)
                """,
                (
                    project_id,
                    owner_user_id,
                    spec["name"],
                    spec["description"],
                    spec["instructions"],
                    spec["default_model_ref"],
                    psycopg.types.json.Jsonb(spec["tool_refs"]),
                    psycopg.types.json.Jsonb(spec["workflow_definition"]),
                    psycopg.types.json.Jsonb(spec["tool_policy"]),
                    psycopg.types.json.Jsonb(spec["runtime_constraints"]),
                    visibility,
                    now,
                    now,
                ),
            )
            cursor.execute(
                """
                INSERT INTO agent_project_versions (
                    project_id,
                    version,
                    spec_json,
                    created_by_user_id,
                    created_at
                )
                VALUES (%s, 1, %s::jsonb, %s, %s)
                """,
                (
                    project_id,
                    psycopg.types.json.Jsonb(spec),
                    owner_user_id,
                    now,
                ),
            )
    row = get_agent_project(database_url, project_id=project_id)
    if row is None:
        raise ValueError("agent_project_create_failed")
    return row


def update_agent_project(
    database_url: str,
    *,
    project_id: str,
    spec: dict[str, Any],
    visibility: str,
    updated_by_user_id: int,
) -> dict[str, Any] | None:
    existing = get_agent_project(database_url, project_id=project_id)
    if existing is None:
        return None
    next_version = int(existing.get("current_version", 1) or 1) + 1
    now = datetime.now(tz=timezone.utc)
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE agent_projects
                SET
                    name = %s,
                    description = %s,
                    instructions = %s,
                    default_model_ref = %s,
                    tool_refs = %s::jsonb,
                    workflow_definition = %s::jsonb,
                    tool_policy = %s::jsonb,
                    runtime_constraints = %s::jsonb,
                    visibility = %s,
                    current_version = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    spec["name"],
                    spec["description"],
                    spec["instructions"],
                    spec["default_model_ref"],
                    psycopg.types.json.Jsonb(spec["tool_refs"]),
                    psycopg.types.json.Jsonb(spec["workflow_definition"]),
                    psycopg.types.json.Jsonb(spec["tool_policy"]),
                    psycopg.types.json.Jsonb(spec["runtime_constraints"]),
                    visibility,
                    next_version,
                    now,
                    project_id,
                ),
            )
            cursor.execute(
                """
                INSERT INTO agent_project_versions (
                    project_id,
                    version,
                    spec_json,
                    created_by_user_id,
                    created_at
                )
                VALUES (%s, %s, %s::jsonb, %s, %s)
                """,
                (
                    project_id,
                    next_version,
                    psycopg.types.json.Jsonb(spec),
                    updated_by_user_id,
                    now,
                ),
            )
    return get_agent_project(database_url, project_id=project_id)


def set_published_agent_id(
    database_url: str,
    *,
    project_id: str,
    published_agent_id: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE agent_projects
                SET published_agent_id = %s, updated_at = %s
                WHERE id = %s
                """,
                (
                    published_agent_id,
                    datetime.now(tz=timezone.utc),
                    project_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
    return get_agent_project(database_url, project_id=project_id)
