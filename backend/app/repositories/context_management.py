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
    backing_provider_instance_id: str | None = None,
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if eligible_only:
        filters.append("kb.lifecycle_state = 'active' AND kb.sync_status = 'ready'")
    if backing_provider_key:
        filters.append("provider.provider_key = %s")
        params.append(backing_provider_key.strip().lower())
    if backing_provider_instance_id:
        filters.append("kb.backing_provider_instance_id = %s")
        params.append(backing_provider_instance_id.strip())
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection(database_url) as connection:
        rows = connection.execute(
            f"""
            SELECT
              kb.*,
              provider.id AS backing_provider_instance_id,
              provider.slug AS backing_provider_slug,
              provider.provider_key AS backing_provider_key,
              provider.display_name AS backing_provider_display_name,
              provider.enabled AS backing_provider_enabled,
              family.capability_key AS backing_provider_capability,
              embedding_provider.slug AS embedding_provider_slug,
              embedding_provider.provider_key AS embedding_provider_key,
              embedding_provider.display_name AS embedding_provider_display_name,
              embedding_provider.enabled AS embedding_provider_enabled,
              embedding_family.capability_key AS embedding_provider_capability,
              COALESCE(usage.binding_count, 0) AS binding_count
            FROM context_knowledge_bases kb
            LEFT JOIN platform_provider_instances provider ON provider.id = kb.backing_provider_instance_id
            LEFT JOIN platform_provider_families family ON family.provider_key = provider.provider_key
            LEFT JOIN platform_provider_instances embedding_provider ON embedding_provider.id = kb.embedding_provider_instance_id
            LEFT JOIN platform_provider_families embedding_family ON embedding_family.provider_key = embedding_provider.provider_key
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


def list_schema_profiles(database_url: str, *, provider_key: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM context_schema_profiles
            WHERE provider_key = %s
            ORDER BY is_system DESC, display_name ASC, slug ASC
            """,
            (provider_key.strip().lower(),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_schema_profile_by_provider_and_slug(
    database_url: str,
    *,
    provider_key: str,
    slug: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM context_schema_profiles
            WHERE provider_key = %s
              AND slug = %s
            """,
            (
                provider_key.strip().lower(),
                slug.strip().lower(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def get_knowledge_base(database_url: str, knowledge_base_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              kb.*,
              provider.id AS backing_provider_instance_id,
              provider.slug AS backing_provider_slug,
              provider.provider_key AS backing_provider_key,
              provider.display_name AS backing_provider_display_name,
              provider.enabled AS backing_provider_enabled,
              family.capability_key AS backing_provider_capability,
              embedding_provider.slug AS embedding_provider_slug,
              embedding_provider.provider_key AS embedding_provider_key,
              embedding_provider.display_name AS embedding_provider_display_name,
              embedding_provider.enabled AS embedding_provider_enabled,
              embedding_family.capability_key AS embedding_provider_capability,
              COALESCE(usage.binding_count, 0) AS binding_count
            FROM context_knowledge_bases kb
            LEFT JOIN platform_provider_instances provider ON provider.id = kb.backing_provider_instance_id
            LEFT JOIN platform_provider_families family ON family.provider_key = provider.provider_key
            LEFT JOIN platform_provider_instances embedding_provider ON embedding_provider.id = kb.embedding_provider_instance_id
            LEFT JOIN platform_provider_families embedding_family ON embedding_family.provider_key = embedding_provider.provider_key
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
            SELECT
              kb.*,
              provider.id AS backing_provider_instance_id,
              provider.slug AS backing_provider_slug,
              provider.provider_key AS backing_provider_key,
              provider.display_name AS backing_provider_display_name,
              provider.enabled AS backing_provider_enabled,
              family.capability_key AS backing_provider_capability,
              embedding_provider.slug AS embedding_provider_slug,
              embedding_provider.provider_key AS embedding_provider_key,
              embedding_provider.display_name AS embedding_provider_display_name,
              embedding_provider.enabled AS embedding_provider_enabled,
              embedding_family.capability_key AS embedding_provider_capability
            FROM context_knowledge_bases
            kb
            LEFT JOIN platform_provider_instances provider ON provider.id = kb.backing_provider_instance_id
            LEFT JOIN platform_provider_families family ON family.provider_key = provider.provider_key
            LEFT JOIN platform_provider_instances embedding_provider ON embedding_provider.id = kb.embedding_provider_instance_id
            LEFT JOIN platform_provider_families embedding_family ON embedding_family.provider_key = embedding_provider.provider_key
            WHERE kb.id = ANY(%s)
            ORDER BY kb.created_at ASC, kb.slug ASC
            """,
            (normalized_ids,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_schema_profile(
    database_url: str,
    *,
    slug: str,
    display_name: str,
    description: str,
    provider_key: str,
    is_system: bool,
    schema_json: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO context_schema_profiles (
                id,
                slug,
                display_name,
                description,
                provider_key,
                is_system,
                schema_json,
                created_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING *
            """,
            (
                str(uuid4()),
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                provider_key.strip().lower(),
                is_system,
                Jsonb(schema_json),
                created_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_schema_profile")
    return dict(row)


def create_knowledge_base(
    database_url: str,
    *,
    slug: str,
    display_name: str,
    description: str,
    index_name: str,
    backing_provider_instance_id: str,
    lifecycle_state: str,
    sync_status: str,
    schema_json: dict[str, Any],
    vectorization_mode: str,
    embedding_provider_instance_id: str | None,
    embedding_resource_id: str | None,
    vectorization_json: dict[str, Any],
    chunking_strategy: str,
    chunking_config_json: dict[str, Any],
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
                backing_provider_instance_id,
                lifecycle_state,
                sync_status,
                schema_json,
                vectorization_mode,
                embedding_provider_instance_id,
                embedding_resource_id,
                vectorization_json,
                chunking_strategy,
                chunking_config_json,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
            RETURNING *
            """,
            (
                str(uuid4()),
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                index_name.strip(),
                backing_provider_instance_id.strip(),
                lifecycle_state.strip().lower(),
                sync_status.strip().lower(),
                Jsonb(schema_json),
                vectorization_mode.strip().lower(),
                embedding_provider_instance_id.strip() if embedding_provider_instance_id else None,
                embedding_resource_id.strip() if embedding_resource_id else None,
                Jsonb(vectorization_json),
                chunking_strategy.strip().lower(),
                Jsonb(chunking_config_json),
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
    chunking_strategy: str,
    chunking_config_json: dict[str, Any],
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
              chunking_strategy = %s,
              chunking_config_json = %s::jsonb,
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
                chunking_strategy.strip().lower(),
                Jsonb(chunking_config_json),
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


def mark_knowledge_base_syncing(
    database_url: str,
    *,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
    last_sync_summary: str | None = None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_bases
            SET
              sync_status = 'syncing',
              last_sync_error = NULL,
              last_sync_summary = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                last_sync_summary.strip() if isinstance(last_sync_summary, str) and last_sync_summary.strip() else None,
                updated_by_user_id,
                knowledge_base_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def set_knowledge_base_sync_result(
    database_url: str,
    *,
    knowledge_base_id: str,
    sync_status: str,
    last_sync_error: str | None,
    last_sync_summary: str | None,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_bases
            SET
              sync_status = %s,
              last_sync_at = NOW(),
              last_sync_error = %s,
              last_sync_summary = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                sync_status.strip().lower(),
                last_sync_error.strip() if isinstance(last_sync_error, str) and last_sync_error.strip() else None,
                last_sync_summary.strip() if isinstance(last_sync_summary, str) and last_sync_summary.strip() else None,
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


def list_source_documents(database_url: str, *, knowledge_base_id: str, source_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM context_documents
            WHERE knowledge_base_id = %s AND source_id = %s
            ORDER BY source_document_key ASC, title ASC
            """,
            (knowledge_base_id.strip(), source_id.strip()),
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


def get_document_by_source_key(
    database_url: str,
    *,
    knowledge_base_id: str,
    source_id: str,
    source_document_key: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM context_documents
            WHERE knowledge_base_id = %s
              AND source_id = %s
              AND source_document_key = %s
            """,
            (
                knowledge_base_id.strip(),
                source_id.strip(),
                source_document_key.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def list_knowledge_sources(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM context_knowledge_sources
            WHERE knowledge_base_id = %s
            ORDER BY created_at ASC, display_name ASC
            """,
            (knowledge_base_id.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_knowledge_source(database_url: str, *, knowledge_base_id: str, source_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM context_knowledge_sources
            WHERE knowledge_base_id = %s AND id = %s
            """,
            (knowledge_base_id.strip(), source_id.strip()),
        ).fetchone()
    return dict(row) if row is not None else None


def create_knowledge_source(
    database_url: str,
    *,
    knowledge_base_id: str,
    source_type: str,
    display_name: str,
    relative_path: str,
    include_globs: list[str],
    exclude_globs: list[str],
    lifecycle_state: str,
    created_by_user_id: int | None,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO context_knowledge_sources (
                id,
                knowledge_base_id,
                source_type,
                display_name,
                relative_path,
                include_globs,
                exclude_globs,
                lifecycle_state,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
            RETURNING *
            """,
            (
                str(uuid4()),
                knowledge_base_id.strip(),
                source_type.strip().lower(),
                display_name.strip(),
                relative_path.strip(),
                Jsonb(include_globs),
                Jsonb(exclude_globs),
                lifecycle_state.strip().lower(),
                created_by_user_id,
                updated_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_knowledge_source")
    return dict(row)


def update_knowledge_source(
    database_url: str,
    *,
    knowledge_base_id: str,
    source_id: str,
    display_name: str,
    relative_path: str,
    include_globs: list[str],
    exclude_globs: list[str],
    lifecycle_state: str,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_sources
            SET
              display_name = %s,
              relative_path = %s,
              include_globs = %s::jsonb,
              exclude_globs = %s::jsonb,
              lifecycle_state = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING *
            """,
            (
                display_name.strip(),
                relative_path.strip(),
                Jsonb(include_globs),
                Jsonb(exclude_globs),
                lifecycle_state.strip().lower(),
                updated_by_user_id,
                knowledge_base_id.strip(),
                source_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_knowledge_source(database_url: str, *, knowledge_base_id: str, source_id: str) -> bool:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            DELETE FROM context_knowledge_sources
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING id
            """,
            (knowledge_base_id.strip(), source_id.strip()),
        ).fetchone()
    return row is not None


def set_knowledge_source_sync_result(
    database_url: str,
    *,
    knowledge_base_id: str,
    source_id: str,
    last_sync_status: str,
    last_sync_error: str | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_sources
            SET
              last_sync_status = %s,
              last_sync_at = NOW(),
              last_sync_error = %s,
              updated_at = NOW()
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING *
            """,
            (
                last_sync_status.strip().lower(),
                last_sync_error.strip() if isinstance(last_sync_error, str) and last_sync_error.strip() else None,
                knowledge_base_id.strip(),
                source_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def mark_knowledge_source_syncing(
    database_url: str,
    *,
    knowledge_base_id: str,
    source_id: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_sources
            SET
              last_sync_status = 'syncing',
              last_sync_error = NULL,
              updated_at = NOW()
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING *
            """,
            (knowledge_base_id.strip(), source_id.strip()),
        ).fetchone()
    return dict(row) if row is not None else None


def create_sync_run(
    database_url: str,
    *,
    knowledge_base_id: str,
    source_id: str | None,
    created_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO context_knowledge_sync_runs (
                id,
                knowledge_base_id,
                source_id,
                status,
                created_by_user_id
            )
            VALUES (%s, %s, %s, 'syncing', %s)
            RETURNING *
            """,
            (
                str(uuid4()),
                knowledge_base_id.strip(),
                source_id.strip() if source_id else None,
                created_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_sync_run")
    return dict(row)


def finish_sync_run(
    database_url: str,
    *,
    run_id: str,
    status: str,
    scanned_file_count: int,
    changed_file_count: int,
    deleted_file_count: int,
    created_document_count: int,
    updated_document_count: int,
    deleted_document_count: int,
    error_summary: str | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_knowledge_sync_runs
            SET
              status = %s,
              scanned_file_count = %s,
              changed_file_count = %s,
              deleted_file_count = %s,
              created_document_count = %s,
              updated_document_count = %s,
              deleted_document_count = %s,
              error_summary = %s,
              finished_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                status.strip().lower(),
                scanned_file_count,
                changed_file_count,
                deleted_file_count,
                created_document_count,
                updated_document_count,
                deleted_document_count,
                error_summary.strip() if isinstance(error_summary, str) and error_summary.strip() else None,
                run_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def list_sync_runs(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
              runs.*,
              sources.display_name AS source_display_name
            FROM context_knowledge_sync_runs runs
            LEFT JOIN context_knowledge_sources sources ON sources.id = runs.source_id
            WHERE runs.knowledge_base_id = %s
            ORDER BY runs.started_at DESC
            """,
            (knowledge_base_id.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]


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
    source_id: str | None = None,
    source_path: str | None = None,
    source_document_key: str | None = None,
    managed_by_source: bool = False,
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
                source_id,
                source_path,
                source_document_key,
                managed_by_source,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
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
                source_id.strip() if source_id else None,
                source_path.strip() if source_path else None,
                source_document_key.strip() if source_document_key else None,
                managed_by_source,
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
    source_id: str | None = None,
    source_path: str | None = None,
    source_document_key: str | None = None,
    managed_by_source: bool | None = None,
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
              source_id = %s,
              source_path = %s,
              source_document_key = %s,
              managed_by_source = COALESCE(%s, managed_by_source),
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
                source_id.strip() if source_id else None,
                source_path.strip() if source_path else None,
                source_document_key.strip() if source_document_key else None,
                managed_by_source,
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


def set_document_chunk_count(
    database_url: str,
    *,
    knowledge_base_id: str,
    document_id: str,
    chunk_count: int,
    updated_by_user_id: int | None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE context_documents
            SET
              chunk_count = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE knowledge_base_id = %s AND id = %s
            RETURNING *
            """,
            (
                chunk_count,
                updated_by_user_id,
                knowledge_base_id.strip(),
                document_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None
