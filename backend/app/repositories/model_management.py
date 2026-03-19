from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from ..db import get_connection


_ALLOWED_ORIGIN = {"platform", "personal"}
_ALLOWED_BACKEND = {"local", "external_api"}
_ALLOWED_SOURCE = {"hf_import", "local_folder", "external_provider"}
_ALLOWED_AVAILABILITY = {"online_only", "offline_ready"}
_ALLOWED_ACCESS = {"private", "assigned", "global"}
_ALLOWED_MODEL_TYPES = {"llm", "embedding"}


def register_model(
    database_url: str,
    *,
    model_id: str,
    name: str,
    provider: str,
    provider_model_id: str | None,
    source_id: str | None,
    local_path: str | None,
    origin_scope: str,
    backend_kind: str,
    source_kind: str,
    availability: str,
    access_scope: str,
    credential_id: str | None,
    model_size_billion: float | None,
    model_type: str | None,
    comment: str | None,
    metadata: dict[str, Any],
    registered_by_user_id: int,
) -> dict[str, Any]:
    origin = origin_scope.strip().lower()
    backend = backend_kind.strip().lower()
    source = source_kind.strip().lower()
    availability_value = availability.strip().lower()
    access = access_scope.strip().lower()
    normalized_model_type = model_type.strip().lower() if model_type else None

    if origin not in _ALLOWED_ORIGIN:
        raise ValueError("invalid_origin_scope")
    if backend not in _ALLOWED_BACKEND:
        raise ValueError("invalid_backend_kind")
    if source not in _ALLOWED_SOURCE:
        raise ValueError("invalid_source_kind")
    if availability_value not in _ALLOWED_AVAILABILITY:
        raise ValueError("invalid_availability")
    if access not in _ALLOWED_ACCESS:
        raise ValueError("invalid_access_scope")
    if normalized_model_type not in _ALLOWED_MODEL_TYPES:
        raise ValueError("invalid_model_type")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_registry (
                model_id, name, provider, source_id, local_path, status, metadata,
                created_by_user_id, registered_by_user_id,
                origin_scope, backend_kind, source_kind, availability, access_scope,
                provider_model_id, credential_id, model_size_billion, model_type, comment,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, 'available', %s::jsonb,
                %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                NOW()
            )
            ON CONFLICT (model_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                provider = EXCLUDED.provider,
                source_id = EXCLUDED.source_id,
                local_path = EXCLUDED.local_path,
                metadata = EXCLUDED.metadata,
                registered_by_user_id = EXCLUDED.registered_by_user_id,
                origin_scope = EXCLUDED.origin_scope,
                backend_kind = EXCLUDED.backend_kind,
                source_kind = EXCLUDED.source_kind,
                availability = EXCLUDED.availability,
                access_scope = EXCLUDED.access_scope,
                provider_model_id = EXCLUDED.provider_model_id,
                credential_id = EXCLUDED.credential_id,
                model_size_billion = EXCLUDED.model_size_billion,
                model_type = EXCLUDED.model_type,
                comment = EXCLUDED.comment,
                updated_at = NOW()
            RETURNING *
            """,
            (
                model_id.strip(),
                name.strip(),
                provider.strip().lower(),
                source_id.strip() if source_id else None,
                local_path.strip() if local_path else None,
                Jsonb(metadata),
                registered_by_user_id,
                registered_by_user_id,
                origin,
                backend,
                source,
                availability_value,
                access,
                provider_model_id.strip() if provider_model_id else None,
                credential_id,
                model_size_billion,
                normalized_model_type,
                comment.strip() if comment else None,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_register_model")
    return dict(row)


def list_models_visible_to_user(
    database_url: str,
    *,
    user_id: int,
    runtime_profile: str,
) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            WITH user_role_cte AS (
                SELECT role
                FROM users
                WHERE id = %s
            ),
            user_groups_cte AS (
                SELECT group_id
                FROM user_group_memberships
                WHERE user_id = %s
            ),
            assigned_models AS (
                SELECT model_id FROM model_user_assignments WHERE user_id = %s
                UNION
                SELECT mga.model_id
                FROM model_group_assignments mga
                JOIN user_groups_cte ug ON ug.group_id = mga.group_id
                UNION
                SELECT model_id FROM model_global_assignments
                UNION
                SELECT jsonb_array_elements_text(msa.model_ids) AS model_id
                FROM model_scope_assignments msa
                JOIN user_role_cte ur ON ur.role = msa.scope
            )
            SELECT DISTINCT m.*
            FROM model_registry m
            LEFT JOIN assigned_models a ON a.model_id = m.model_id
            WHERE
                m.is_enabled = TRUE
                AND (
                    (m.origin_scope = 'personal' AND m.registered_by_user_id = %s)
                    OR (m.origin_scope = 'platform' AND (
                        m.access_scope = 'global'
                        OR (m.access_scope = 'assigned' AND a.model_id IS NOT NULL)
                        OR (m.access_scope = 'private' AND m.registered_by_user_id = %s)
                    ))
                )
                AND (
                    %s <> 'offline'
                    OR m.backend_kind = 'local'
                    OR m.availability = 'offline_ready'
                )
            ORDER BY m.updated_at DESC, m.model_id ASC
            """,
            (user_id, user_id, user_id, user_id, user_id, runtime_profile.strip().lower()),
        ).fetchall()
    return [dict(row) for row in rows]


def get_model_by_id(database_url: str, model_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT * FROM model_registry WHERE model_id = %s",
            (model_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def assign_model_to_user(
    database_url: str,
    *,
    model_id: str,
    user_id: int,
    actor_user_id: int,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_user_assignments (model_id, user_id, assigned_by_user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (model_id, user_id)
            DO UPDATE SET assigned_by_user_id = EXCLUDED.assigned_by_user_id
            RETURNING model_id, user_id, assigned_by_user_id, created_at
            """,
            (model_id.strip(), user_id, actor_user_id),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_assign_model")
    return dict(row)


def append_audit_event(
    database_url: str,
    *,
    actor_user_id: int | None,
    event_type: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
) -> None:
    with get_connection(database_url) as connection:
        connection.execute(
            """
            INSERT INTO model_audit_log (actor_user_id, event_type, target_type, target_id, payload, event_hash)
            VALUES (%s, %s, %s, %s, %s::jsonb, decode(repeat('00', 32), 'hex'))
            """,
            (actor_user_id, event_type.strip(), target_type.strip(), target_id.strip(), Jsonb(payload)),
        )
