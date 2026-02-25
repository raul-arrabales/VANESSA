from __future__ import annotations

from typing import Any

from psycopg import errors

from ..db import get_connection

_SCOPE_TYPES = {"org", "group", "user"}


def register_model_definition(
    database_url: str,
    *,
    model_id: str,
    provider: str,
    metadata: dict[str, Any],
    provider_config_ref: str | None,
    created_by_user_id: int,
) -> dict[str, Any]:
    if not model_id.strip():
        raise ValueError("model_id_required")
    if not provider.strip():
        raise ValueError("provider_required")

    with get_connection(database_url) as connection:
        try:
            row = connection.execute(
                """
                INSERT INTO model_registry (
                    model_id,
                    provider,
                    metadata,
                    provider_config_ref,
                    created_by_user_id
                )
                VALUES (%s, %s, %s::jsonb, %s, %s)
                RETURNING *
                """,
                (
                    model_id.strip(),
                    provider.strip(),
                    metadata,
                    provider_config_ref.strip() if provider_config_ref else None,
                    created_by_user_id,
                ),
            ).fetchone()
        except errors.UniqueViolation as exc:
            raise ValueError("duplicate_model") from exc

    if row is None:
        raise RuntimeError("failed_to_register_model")
    return dict(row)


def find_model_definition(database_url: str, model_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT * FROM model_registry WHERE model_id = %s", (model_id.strip(),)
        ).fetchone()
    return dict(row) if row else None


def assign_model_access(
    database_url: str,
    *,
    model_id: str,
    scope_type: str,
    scope_id: str,
    assigned_by_user_id: int,
) -> dict[str, Any]:
    if scope_type not in _SCOPE_TYPES:
        raise ValueError("invalid_scope_type")
    if not scope_id.strip():
        raise ValueError("scope_id_required")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_access_assignments (
                model_id,
                scope_type,
                scope_id,
                assigned_by_user_id
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (model_id, scope_type, scope_id)
            DO UPDATE SET
                assigned_by_user_id = EXCLUDED.assigned_by_user_id,
                updated_at = NOW()
            RETURNING *
            """,
            (model_id.strip(), scope_type, scope_id.strip(), assigned_by_user_id),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_assign_model_access")
    return dict(row)


def list_effective_allowed_models(
    database_url: str,
    *,
    user_id: int,
    org_id: str | None,
    group_id: str | None,
) -> list[dict[str, Any]]:
    scope_filters: list[tuple[str, str]] = [("user", str(user_id))]
    if org_id:
        scope_filters.append(("org", org_id.strip()))
    if group_id:
        scope_filters.append(("group", group_id.strip()))

    where_clauses: list[str] = []
    params: list[Any] = []
    for scope_type, scope_id in scope_filters:
        where_clauses.append("(a.scope_type = %s AND a.scope_id = %s)")
        params.extend([scope_type, scope_id])

    query = f"""
        SELECT DISTINCT m.*
        FROM model_registry m
        INNER JOIN model_access_assignments a
            ON a.model_id = m.model_id
        WHERE {' OR '.join(where_clauses)}
        ORDER BY m.model_id ASC
    """

    with get_connection(database_url) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
