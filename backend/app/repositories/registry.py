from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from ..db import get_connection

_ENTITY_TYPES = {"model", "agent", "tool"}
_SHARE_PERMISSIONS = {"view", "fork", "execute", "admin"}
_GRANTEE_TYPES = {"user", "group", "org", "public"}
_RUNTIME_PROFILES = {"online", "offline", "air_gapped"}


def create_registry_entity(
    database_url: str,
    *,
    entity_id: str,
    entity_type: str,
    owner_user_id: int,
    visibility: str = "private",
    status: str = "draft",
) -> dict[str, Any]:
    normalized_type = entity_type.strip().lower()
    if normalized_type not in _ENTITY_TYPES:
        raise ValueError("invalid_entity_type")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO registry_entities (entity_id, entity_type, owner_user_id, visibility, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (entity_id.strip(), normalized_type, owner_user_id, visibility.strip().lower(), status.strip().lower()),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_create_registry_entity")
    return dict(row)


def list_registry_entities(database_url: str, *, entity_type: str) -> list[dict[str, Any]]:
    normalized_type = entity_type.strip().lower()
    if normalized_type not in _ENTITY_TYPES:
        raise ValueError("invalid_entity_type")

    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT e.*, v.version AS current_version, v.spec_json AS current_spec, v.published_at
            FROM registry_entities e
            LEFT JOIN registry_versions v
              ON v.entity_id = e.entity_id AND v.is_current = TRUE
            WHERE e.entity_type = %s
            ORDER BY e.updated_at DESC, e.entity_id ASC
            """,
            (normalized_type,),
        ).fetchall()
    return [dict(row) for row in rows]


def find_registry_entity(database_url: str, *, entity_type: str, entity_id: str) -> dict[str, Any] | None:
    normalized_type = entity_type.strip().lower()
    if normalized_type not in _ENTITY_TYPES:
        raise ValueError("invalid_entity_type")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT e.*, v.version AS current_version, v.spec_json AS current_spec, v.published_at
            FROM registry_entities e
            LEFT JOIN registry_versions v
              ON v.entity_id = e.entity_id AND v.is_current = TRUE
            WHERE e.entity_type = %s AND e.entity_id = %s
            """,
            (normalized_type, entity_id.strip()),
        ).fetchone()
    return dict(row) if row else None


def create_registry_version(
    database_url: str,
    *,
    entity_id: str,
    version: str,
    spec_json: dict[str, Any],
    set_current: bool = True,
    published: bool = False,
) -> dict[str, Any]:
    entity_id_value = entity_id.strip()
    version_value = version.strip()
    if not entity_id_value:
        raise ValueError("entity_id_required")
    if not version_value:
        raise ValueError("version_required")

    with get_connection(database_url) as connection:
        if set_current:
            connection.execute(
                "UPDATE registry_versions SET is_current = FALSE WHERE entity_id = %s",
                (entity_id_value,),
            )

        row = connection.execute(
            """
            INSERT INTO registry_versions (version_id, entity_id, version, spec_json, is_current, published_at)
            VALUES (%s, %s, %s, %s::jsonb, %s, CASE WHEN %s THEN NOW() ELSE NULL END)
            RETURNING *
            """,
            (
                str(uuid4()),
                entity_id_value,
                version_value,
                Jsonb(spec_json),
                set_current,
                published,
            ),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_create_registry_version")
    return dict(row)


def list_registry_versions(database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM registry_versions
            WHERE entity_id = %s
            ORDER BY created_at DESC, version DESC
            """,
            (entity_id.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


def create_share_grant(
    database_url: str,
    *,
    entity_id: str,
    grantee_type: str,
    grantee_id: str | None,
    permission: str,
    shared_by_user_id: int,
) -> dict[str, Any]:
    normalized_grantee = grantee_type.strip().lower()
    normalized_permission = permission.strip().lower()
    if normalized_grantee not in _GRANTEE_TYPES:
        raise ValueError("invalid_grantee_type")
    if normalized_permission not in _SHARE_PERMISSIONS:
        raise ValueError("invalid_permission")

    grantee_id_value = (grantee_id or "").strip()
    if normalized_grantee != "public" and not grantee_id_value:
        raise ValueError("grantee_id_required")
    if normalized_grantee == "public":
        grantee_id_value = ""

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO entity_shares (entity_id, grantee_type, grantee_id, permission, shared_by_user_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (entity_id, grantee_type, grantee_id, permission)
            DO UPDATE SET
              shared_by_user_id = EXCLUDED.shared_by_user_id,
              updated_at = NOW()
            RETURNING *
            """,
            (
                entity_id.strip(),
                normalized_grantee,
                grantee_id_value,
                normalized_permission,
                shared_by_user_id,
            ),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_create_share_grant")
    return dict(row)


def list_share_grants(database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT entity_id, grantee_type, grantee_id, permission, shared_by_user_id, created_at, updated_at
            FROM entity_shares
            WHERE entity_id = %s
            ORDER BY created_at DESC
            """,
            (entity_id.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_runtime_profile(database_url: str, *, profile: str, updated_by_user_id: int | None) -> str:
    normalized_profile = profile.strip().lower()
    if normalized_profile not in _RUNTIME_PROFILES:
        raise ValueError("invalid_runtime_profile")

    with get_connection(database_url) as connection:
        connection.execute(
            """
            INSERT INTO system_runtime_config (config_key, config_value, updated_by_user_id)
            VALUES ('runtime_profile', %s, %s)
            ON CONFLICT (config_key)
            DO UPDATE SET
              config_value = EXCLUDED.config_value,
              updated_by_user_id = EXCLUDED.updated_by_user_id,
              updated_at = NOW()
            """,
            (normalized_profile, updated_by_user_id),
        )
    return normalized_profile


def get_runtime_profile(database_url: str) -> str | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT config_value FROM system_runtime_config WHERE config_key = 'runtime_profile'"
        ).fetchone()
    if not row:
        return None
    value = str(row.get("config_value", "")).strip().lower()
    return value if value in _RUNTIME_PROFILES else None


def list_entity_permissions_for_user(
    database_url: str,
    *,
    entity_id: str,
    user_id: int,
) -> set[str]:
    with get_connection(database_url) as connection:
        entity_row = connection.execute(
            "SELECT owner_user_id, visibility FROM registry_entities WHERE entity_id = %s",
            (entity_id.strip(),),
        ).fetchone()
        if entity_row is None:
            return set()

        owner_user_id = entity_row.get("owner_user_id")
        visibility = str(entity_row.get("visibility", "private")).strip().lower()
        permissions: set[str] = set()

        if owner_user_id is not None and int(owner_user_id) == int(user_id):
            return {"view", "fork", "execute", "admin"}

        if visibility in {"public", "unlisted"}:
            permissions.add("view")

        rows = connection.execute(
            """
            SELECT permission
            FROM entity_shares
            WHERE entity_id = %s
              AND ((grantee_type = 'public') OR (grantee_type = 'user' AND grantee_id = %s))
            """,
            (entity_id.strip(), str(user_id)),
        ).fetchall()

        for row in rows:
            permission = str(row.get("permission", "")).strip().lower()
            if permission in _SHARE_PERMISSIONS:
                permissions.add(permission)

    return permissions
