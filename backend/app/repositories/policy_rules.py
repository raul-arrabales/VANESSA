from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from ..db import get_connection

_VALID_EFFECTS = {"allow", "deny"}


def create_policy_rule(
    database_url: str,
    *,
    scope_type: str,
    scope_id: str,
    resource_type: str,
    resource_id: str,
    effect: str,
    rule_json: dict[str, Any],
) -> dict[str, Any]:
    normalized_effect = effect.strip().lower()
    if normalized_effect not in _VALID_EFFECTS:
        raise ValueError("invalid_effect")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO policy_rules (scope_type, scope_id, resource_type, resource_id, effect, rule_json)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            RETURNING *
            """,
            (
                scope_type.strip().lower(),
                scope_id.strip(),
                resource_type.strip().lower(),
                resource_id.strip(),
                normalized_effect,
                Jsonb(rule_json),
            ),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_create_policy_rule")
    return dict(row)


def list_policy_rules(
    database_url: str,
    *,
    scope_type: str | None = None,
    scope_id: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM policy_rules
    """
    params: list[Any] = []
    clauses: list[str] = []

    if scope_type:
        clauses.append("scope_type = %s")
        params.append(scope_type.strip().lower())
    if scope_id:
        clauses.append("scope_id = %s")
        params.append(scope_id.strip())

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, id DESC"

    with get_connection(database_url) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def evaluate_policy(
    database_url: str,
    *,
    user_id: int,
    resource_type: str,
    resource_id: str,
    action: str,
) -> str | None:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT effect, rule_json
            FROM policy_rules
            WHERE scope_type = 'user'
              AND scope_id = %s
              AND resource_type = %s
              AND (resource_id = %s OR resource_id = '*')
            ORDER BY created_at DESC
            """,
            (str(user_id), resource_type.strip().lower(), resource_id.strip()),
        ).fetchall()

    decision: str | None = None
    for row in rows:
        rule_json = row.get("rule_json") if isinstance(row.get("rule_json"), dict) else {}
        rule_action = str(rule_json.get("action", "*")).strip().lower() or "*"
        if rule_action not in {"*", action.strip().lower()}:
            continue

        effect = str(row.get("effect", "")).strip().lower()
        if effect == "deny":
            return "deny"
        if effect == "allow":
            decision = "allow"

    return decision
