from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from ..db import get_connection

_SCOPES = ("user", "admin", "superadmin")


def list_scope_assignments(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT scope, model_ids
            FROM model_scope_assignments
            ORDER BY CASE scope
                WHEN 'user' THEN 1
                WHEN 'admin' THEN 2
                WHEN 'superadmin' THEN 3
                ELSE 99
            END
            """
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_scope_assignment(
    database_url: str,
    *,
    scope: str,
    model_ids: list[str],
    updated_by_user_id: int,
) -> dict[str, Any]:
    scope_value = scope.strip().lower()
    if scope_value not in _SCOPES:
        raise ValueError("invalid_scope")

    unique_ids: list[str] = []
    seen: set[str] = set()
    for model_id in model_ids:
        normalized = model_id.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_ids.append(normalized)

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_scope_assignments (scope, model_ids, updated_by_user_id)
            VALUES (%s, %s::jsonb, %s)
            ON CONFLICT (scope)
            DO UPDATE SET
                model_ids = EXCLUDED.model_ids,
                updated_by_user_id = EXCLUDED.updated_by_user_id,
                updated_at = NOW()
            RETURNING scope, model_ids
            """,
            (scope_value, Jsonb(unique_ids), updated_by_user_id),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_update_assignment")
    return dict(row)
