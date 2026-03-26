from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from ..db import get_connection


def list_knowledge_bases(
    database_url: str,
    *,
    eligible_only: bool = False,
    backing_provider_key: str | None = None,
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if eligible_only:
        filters.append("kb.lifecycle_state = 'active' AND kb.sync_status = 'ready'")
    if backing_provider_key:
        filters.append("kb.backing_provider_key = %s")
        params.append(backing_provider_key.strip().lower())
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection(database_url) as connection:
        rows = connection.execute(
            f"""
            SELECT
              kb.*,
              COALESCE(usage.binding_count, 0) AS binding_count
            FROM context_knowledge_bases kb
            LEFT JOIN (
              SELECT
                knowledge_base_id,
                COUNT(DISTINCT binding_id) AS binding_count
              FROM platform_binding_resources
              WHERE knowledge_base_id IS NOT NULL
              GROUP BY knowledge_base_id
            ) usage ON usage.knowledge_base_id = kb.id
            {where_clause}
            ORDER BY kb.created_at ASC, kb.slug ASC
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def get_knowledge_base(database_url: str, knowledge_base_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              kb.*,
              COALESCE(usage.binding_count, 0) AS binding_count
            FROM context_knowledge_bases kb
            LEFT JOIN (
              SELECT
                knowledge_base_id,
                COUNT(DISTINCT binding_id) AS binding_count
              FROM platform_binding_resources
              WHERE knowledge_base_id IS NOT NULL
              GROUP BY knowledge_base_id
            ) usage ON usage.knowledge_base_id = kb.id
            WHERE kb.id = %s
            """,
            (knowledge_base_id.strip(),),
        ).fetchone()
    return dict(row) if row is not None else None


def get_knowledge_bases(database_url: str, knowledge_base_ids: list[str]) -> list[dict[str, Any]]:
    normalized_ids = [item.strip() for item in knowledge_base_ids if item.strip()]
    if not normalized_ids:
        return []
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM context_knowledge_bases
            WHERE id = ANY(%s)
            ORDER BY created_at ASC, slug ASC
            """,
            (normalized_ids,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_knowledge_base(
    database_url: str,
    *,
    slug: str,
    display_name: str,
    description: str,
    index_name: str,
    backing_provider_key: str,
    lifecycle_state: str,
    sync_status: str,
    schema_json: dict[str, Any],
    created_by_user_id: int | None,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO context_knowledge_bases (
                id,
                slug,
                display_name,
                description,
                index_name,
                backing_provider_key,
                lifecycle_state,
                sync_status,
                schema_json,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING *
            """,
            (
                str(uuid4()),
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                index_name.strip(),
                backing_provider_key.strip().lower(),
                lifecycle_state.strip().lower(),
                sync_status.strip().lower(),
                Jsonb(schema_json),
                created_by_user_id,
                updated_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_knowledge_base")
    return dict(row)


def update_knowledge_base(
    database_url: str,
    *,
    knowledge_base_id: str,
    slug: str,
    display_name: str,
    description: str,
    lifecycle_state: str,
    sync_status: str,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_bases
            SET
              slug = %s,
              display_name = %s,
              description = %s,
              lifecycle_state = %s,
              sync_status = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                lifecycle_state.strip().lower(),
                sync_status.strip().lower(),
                updated_by_user_id,
                knowledge_base_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def set_knowledge_base_sync_status(
    database_url: str,
    *,
    knowledge_base_id: str,
    sync_status: str,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_bases
            SET
              sync_status = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                sync_status.strip().lower(),
                updated_by_user_id,
                knowledge_base_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_knowledge_base(database_url: str, knowledge_base_id: str) -> bool:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            DELETE FROM context_knowledge_bases
            WHERE id = %s
            RETURNING id
            """,
            (knowledge_base_id.strip(),),
        ).fetchone()
    return row is not None


def count_deployment_bindings_for_knowledge_base(database_url: str, *, knowledge_base_id: str) -> int:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT binding_id) AS binding_count
            FROM platform_binding_resources
            WHERE knowledge_base_id = %s
            """,
            (knowledge_base_id.strip(),),
        ).fetchone()
    return int(row["binding_count"]) if row is not None else 0


def list_knowledge_base_deployment_usage(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT
              p.id AS deployment_profile_id,
              p.slug AS deployment_profile_slug,
              p.display_name AS deployment_profile_display_name,
              b.capability_key
            FROM platform_binding_resources br
            JOIN platform_deployment_bindings b ON b.id = br.binding_id
            JOIN platform_deployment_profiles p ON p.id = b.deployment_profile_id
            WHERE br.knowledge_base_id = %s
            ORDER BY p.slug ASC, b.capability_key ASC
            """,
            (knowledge_base_id.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


def list_documents(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM context_documents
            WHERE knowledge_base_id = %s
            ORDER BY created_at DESC, title ASC
            """,
            (knowledge_base_id.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(database_url: str, *, knowledge_base_id: str, document_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM context_documents
            WHERE knowledge_base_id = %s AND id = %s
            """,
            (knowledge_base_id.strip(), document_id.strip()),
        ).fetchone()
    return dict(row) if row is not None else None


def create_document(
    database_url: str,
    *,
    document_id: str | None = None,
    knowledge_base_id: str,
    title: str,
    source_type: str,
    source_name: str | None,
    uri: str | None,
    text: str,
    metadata_json: dict[str, Any],
    chunk_count: int,
    created_by_user_id: int | None,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO context_documents (
                id,
                knowledge_base_id,
                title,
                source_type,
                source_name,
                uri,
                text,
                metadata_json,
                chunk_count,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            RETURNING *
            """,
            (
                document_id.strip() if document_id else str(uuid4()),
                knowledge_base_id.strip(),
                title.strip(),
                source_type.strip(),
                source_name.strip() if source_name else None,
                uri.strip() if uri else None,
                text,
                Jsonb(metadata_json),
                chunk_count,
                created_by_user_id,
                updated_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_document")
    return dict(row)


def update_document(
    database_url: str,
    *,
    knowledge_base_id: str,
    document_id: str,
    title: str,
    source_type: str,
    source_name: str | None,
    uri: str | None,
    text: str,
    metadata_json: dict[str, Any],
    chunk_count: int,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_documents
            SET
              title = %s,
              source_type = %s,
              source_name = %s,
              uri = %s,
              text = %s,
              metadata_json = %s::jsonb,
              chunk_count = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING *
            """,
            (
                title.strip(),
                source_type.strip(),
                source_name.strip() if source_name else None,
                uri.strip() if uri else None,
                text,
                Jsonb(metadata_json),
                chunk_count,
                updated_by_user_id,
                knowledge_base_id.strip(),
                document_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_document(database_url: str, *, knowledge_base_id: str, document_id: str) -> bool:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            DELETE FROM context_documents
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING id
            """,
            (knowledge_base_id.strip(), document_id.strip()),
        ).fetchone()
    return row is not None


def set_knowledge_base_document_count(
    database_url: str,
    *,
    knowledge_base_id: str,
    document_count: int,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_bases
            SET
              document_count = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                document_count,
                updated_by_user_id,
                knowledge_base_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None
