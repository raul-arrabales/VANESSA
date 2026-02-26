from __future__ import annotations

from typing import Any

from psycopg import errors
from psycopg.types.json import Jsonb

from ..db import get_connection

_ALLOWED_STATUSES = {"available", "downloading", "failed", "archived"}


def list_model_catalog(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
                model_id,
                name,
                provider,
                source_id,
                local_path,
                status,
                metadata,
                created_at,
                updated_at
            FROM model_registry
            ORDER BY updated_at DESC, model_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_model_catalog_item(
    database_url: str,
    *,
    model_id: str,
    name: str,
    provider: str,
    source_id: str | None,
    local_path: str | None,
    status: str,
    metadata: dict[str, Any],
    created_by_user_id: int,
) -> dict[str, Any]:
    model_id_value = model_id.strip()
    name_value = name.strip()
    provider_value = provider.strip().lower()
    status_value = status.strip().lower()

    if not model_id_value:
        raise ValueError("model_id_required")
    if not name_value:
        raise ValueError("name_required")
    if not provider_value:
        raise ValueError("invalid_provider")
    if status_value not in _ALLOWED_STATUSES:
        raise ValueError("invalid_status")

    with get_connection(database_url) as connection:
        try:
            row = connection.execute(
                """
                INSERT INTO model_registry (
                    model_id,
                    name,
                    provider,
                    source_id,
                    local_path,
                    status,
                    metadata,
                    created_by_user_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                RETURNING *
                """,
                (
                    model_id_value,
                    name_value,
                    provider_value,
                    source_id.strip() if source_id else None,
                    local_path.strip() if local_path else None,
                    status_value,
                    Jsonb(metadata),
                    created_by_user_id,
                ),
            ).fetchone()
        except errors.UniqueViolation as exc:
            raise ValueError("duplicate_model") from exc

    if row is None:
        raise RuntimeError("failed_to_create_model")
    return dict(row)


def get_model_catalog_item(database_url: str, model_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT * FROM model_registry WHERE model_id = %s",
            (model_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def upsert_model_catalog_item(
    database_url: str,
    *,
    model_id: str,
    name: str,
    provider: str,
    source_id: str | None,
    local_path: str | None,
    status: str,
    metadata: dict[str, Any],
    updated_by_user_id: int | None = None,
) -> dict[str, Any]:
    model_id_value = model_id.strip()
    name_value = name.strip()
    provider_value = provider.strip().lower()
    status_value = status.strip().lower()

    if not model_id_value:
        raise ValueError("model_id_required")
    if not name_value:
        raise ValueError("name_required")
    if not provider_value:
        raise ValueError("invalid_provider")
    if status_value not in _ALLOWED_STATUSES:
        raise ValueError("invalid_status")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_registry (
                model_id,
                name,
                provider,
                source_id,
                local_path,
                status,
                metadata,
                created_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (model_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                provider = EXCLUDED.provider,
                source_id = EXCLUDED.source_id,
                local_path = EXCLUDED.local_path,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                created_by_user_id = COALESCE(model_registry.created_by_user_id, EXCLUDED.created_by_user_id),
                updated_at = NOW()
            RETURNING *
            """,
            (
                model_id_value,
                name_value,
                provider_value,
                source_id.strip() if source_id else None,
                local_path.strip() if local_path else None,
                status_value,
                Jsonb(metadata),
                updated_by_user_id,
            ),
        ).fetchone()

    if row is None:
        raise RuntimeError("failed_to_upsert_model")
    return dict(row)
