from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from ..db import get_connection

_CAPABILITIES = {"llm_inference", "embeddings", "vector_store", "mcp_runtime", "sandbox_execution"}


def ensure_capability(
    database_url: str,
    *,
    capability_key: str,
    display_name: str,
    description: str,
    is_required: bool,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO platform_capabilities (
                capability_key,
                display_name,
                description,
                is_required
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (capability_key)
            DO UPDATE SET
              display_name = EXCLUDED.display_name,
              description = EXCLUDED.description,
              is_required = EXCLUDED.is_required,
              updated_at = NOW()
            RETURNING *
            """,
            (
                capability_key.strip().lower(),
                display_name.strip(),
                description.strip(),
                is_required,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_ensure_capability")
    return dict(row)


def list_capabilities(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT capability_key, display_name, description, is_required, created_at, updated_at
            FROM platform_capabilities
            ORDER BY capability_key ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def ensure_provider_family(
    database_url: str,
    *,
    provider_key: str,
    capability_key: str,
    adapter_kind: str,
    display_name: str,
    description: str,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO platform_provider_families (
                provider_key,
                capability_key,
                adapter_kind,
                display_name,
                description
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (provider_key)
            DO UPDATE SET
              capability_key = EXCLUDED.capability_key,
              adapter_kind = EXCLUDED.adapter_kind,
              display_name = EXCLUDED.display_name,
              description = EXCLUDED.description,
              updated_at = NOW()
            RETURNING *
            """,
            (
                provider_key.strip().lower(),
                capability_key.strip().lower(),
                adapter_kind.strip().lower(),
                display_name.strip(),
                description.strip(),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_ensure_provider_family")
    return dict(row)


def list_provider_families(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
              provider_key,
              capability_key,
              adapter_kind,
              display_name,
              description,
              created_at,
              updated_at
            FROM platform_provider_families
            ORDER BY capability_key ASC, provider_key ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_provider_family(database_url: str, provider_key: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              provider_key,
              capability_key,
              adapter_kind,
              display_name,
              description,
              created_at,
              updated_at
            FROM platform_provider_families
            WHERE provider_key = %s
            """,
            (provider_key.strip().lower(),),
        ).fetchone()
    return dict(row) if row is not None else None


def ensure_provider_instance(
    database_url: str,
    *,
    slug: str,
    provider_key: str,
    display_name: str,
    description: str,
    endpoint_url: str,
    healthcheck_url: str | None,
    enabled: bool,
    config_json: dict[str, Any],
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM platform_provider_instances
            WHERE slug = %s
            """,
            (slug.strip().lower(),),
        ).fetchone()
        provider_id = str(existing["id"]) if existing is not None else str(uuid4())
        row = connection.execute(
            """
            INSERT INTO platform_provider_instances (
                id,
                slug,
                provider_key,
                display_name,
                description,
                endpoint_url,
                healthcheck_url,
                enabled,
                config_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (slug)
            DO UPDATE SET
              provider_key = EXCLUDED.provider_key,
              display_name = EXCLUDED.display_name,
              description = EXCLUDED.description,
              endpoint_url = EXCLUDED.endpoint_url,
              healthcheck_url = EXCLUDED.healthcheck_url,
              enabled = EXCLUDED.enabled,
              config_json = EXCLUDED.config_json,
              updated_at = NOW()
            RETURNING *
            """,
            (
                provider_id,
                slug.strip().lower(),
                provider_key.strip().lower(),
                display_name.strip(),
                description.strip(),
                endpoint_url.strip(),
                (healthcheck_url or "").strip() or None,
                enabled,
                Jsonb(config_json),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_ensure_provider_instance")
    return dict(row)


def create_provider_instance(
    database_url: str,
    *,
    slug: str,
    provider_key: str,
    display_name: str,
    description: str,
    endpoint_url: str,
    healthcheck_url: str | None,
    enabled: bool,
    config_json: dict[str, Any],
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO platform_provider_instances (
                id,
                slug,
                provider_key,
                display_name,
                description,
                endpoint_url,
                healthcheck_url,
                enabled,
                config_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING *
            """,
            (
                str(uuid4()),
                slug.strip().lower(),
                provider_key.strip().lower(),
                display_name.strip(),
                description.strip(),
                endpoint_url.strip(),
                (healthcheck_url or "").strip() or None,
                enabled,
                Jsonb(config_json),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_provider_instance")
    return dict(row)


def update_provider_instance(
    database_url: str,
    *,
    provider_instance_id: str,
    slug: str,
    display_name: str,
    description: str,
    endpoint_url: str,
    healthcheck_url: str | None,
    enabled: bool,
    config_json: dict[str, Any],
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE platform_provider_instances
            SET
              slug = %s,
              display_name = %s,
              description = %s,
              endpoint_url = %s,
              healthcheck_url = %s,
              enabled = %s,
              config_json = %s::jsonb,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                endpoint_url.strip(),
                (healthcheck_url or "").strip() or None,
                enabled,
                Jsonb(config_json),
                provider_instance_id.strip(),
            ),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_provider_instance(database_url: str, provider_instance_id: str) -> bool:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            DELETE FROM platform_provider_instances
            WHERE id = %s
            RETURNING id
            """,
            (provider_instance_id.strip(),),
        ).fetchone()
    return row is not None


def list_provider_instances(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
              i.id,
              i.slug,
              i.provider_key,
              f.capability_key,
              f.adapter_kind,
              i.display_name,
              i.description,
              i.endpoint_url,
              i.healthcheck_url,
              i.enabled,
              i.config_json,
              i.created_at,
              i.updated_at
            FROM platform_provider_instances i
            JOIN platform_provider_families f ON f.provider_key = i.provider_key
            ORDER BY f.capability_key ASC, i.slug ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_provider_instance(database_url: str, provider_instance_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              i.id,
              i.slug,
              i.provider_key,
              f.capability_key,
              f.adapter_kind,
              i.display_name,
              i.description,
              i.endpoint_url,
              i.healthcheck_url,
              i.enabled,
              i.config_json,
              i.created_at,
              i.updated_at
            FROM platform_provider_instances i
            JOIN platform_provider_families f ON f.provider_key = i.provider_key
            WHERE i.id = %s
            """,
            (provider_instance_id.strip(),),
        ).fetchone()
    return dict(row) if row is not None else None


def count_deployment_bindings_for_provider(database_url: str, *, provider_instance_id: str) -> int:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS binding_count
            FROM platform_deployment_bindings
            WHERE provider_instance_id = %s
            """,
            (provider_instance_id.strip(),),
        ).fetchone()
    return int(row["binding_count"]) if row is not None else 0


def count_deployment_bindings_for_managed_model(database_url: str, *, model_id: str) -> int:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS binding_count
            FROM platform_binding_resources
            WHERE managed_model_id = %s
            """,
            (model_id.strip(),),
        ).fetchone()
    return int(row["binding_count"]) if row is not None else 0


def ensure_deployment_profile(
    database_url: str,
    *,
    slug: str,
    display_name: str,
    description: str,
    created_by_user_id: int | None,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM platform_deployment_profiles
            WHERE slug = %s
            """,
            (slug.strip().lower(),),
        ).fetchone()
        deployment_id = str(existing["id"]) if existing is not None else str(uuid4())
        row = connection.execute(
            """
            INSERT INTO platform_deployment_profiles (
                id,
                slug,
                display_name,
                description,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug)
            DO UPDATE SET
              display_name = EXCLUDED.display_name,
              description = EXCLUDED.description,
              updated_by_user_id = EXCLUDED.updated_by_user_id,
              updated_at = NOW()
            RETURNING *
            """,
            (
                deployment_id,
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                created_by_user_id,
                updated_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_ensure_deployment_profile")
    return dict(row)


def create_deployment_profile(
    database_url: str,
    *,
    slug: str,
    display_name: str,
    description: str,
    bindings: list[dict[str, Any]],
    created_by_user_id: int,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        profile_row = connection.execute(
            """
            INSERT INTO platform_deployment_profiles (
                id,
                slug,
                display_name,
                description,
                created_by_user_id,
                updated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(uuid4()),
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                created_by_user_id,
                created_by_user_id,
            ),
        ).fetchone()
        if profile_row is None:
            raise RuntimeError("failed_to_create_deployment_profile")

        for binding in bindings:
            binding_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO platform_deployment_bindings (
                    id,
                    deployment_profile_id,
                    capability_key,
                    provider_instance_id,
                    binding_config,
                    resource_policy
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    binding_id,
                    str(profile_row["id"]),
                    str(binding["capability_key"]).strip().lower(),
                    str(binding["provider_instance_id"]).strip(),
                    Jsonb(binding.get("binding_config") or {}),
                    Jsonb(binding.get("resource_policy") or {}),
                ),
            )
            _replace_binding_resources(
                connection,
                binding_id=binding_id,
                resources=binding.get("resources") or [],
                default_resource_id=str(binding.get("default_resource_id") or "").strip() or None,
            )
    return get_deployment_profile(database_url, str(profile_row["id"])) or {}


def update_deployment_profile(
    database_url: str,
    *,
    deployment_profile_id: str,
    slug: str,
    display_name: str,
    description: str,
    bindings: list[dict[str, Any]],
    updated_by_user_id: int,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        profile_row = connection.execute(
            """
            UPDATE platform_deployment_profiles
            SET
              slug = %s,
              display_name = %s,
              description = %s,
              updated_by_user_id = %s,
              updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                slug.strip().lower(),
                display_name.strip(),
                description.strip(),
                updated_by_user_id,
                deployment_profile_id.strip(),
            ),
        ).fetchone()
        if profile_row is None:
            return None

        connection.execute(
            """
            DELETE FROM platform_deployment_bindings
            WHERE deployment_profile_id = %s
            """,
            (deployment_profile_id.strip(),),
        )
        for binding in bindings:
            binding_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO platform_deployment_bindings (
                    id,
                    deployment_profile_id,
                    capability_key,
                    provider_instance_id,
                    binding_config,
                    resource_policy
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    binding_id,
                    deployment_profile_id.strip(),
                    str(binding["capability_key"]).strip().lower(),
                    str(binding["provider_instance_id"]).strip(),
                    Jsonb(binding.get("binding_config") or {}),
                    Jsonb(binding.get("resource_policy") or {}),
                ),
            )
            _replace_binding_resources(
                connection,
                binding_id=binding_id,
                resources=binding.get("resources") or [],
                default_resource_id=str(binding.get("default_resource_id") or "").strip() or None,
            )
    return get_deployment_profile(database_url, deployment_profile_id.strip())


def delete_deployment_profile(database_url: str, deployment_profile_id: str) -> bool:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            DELETE FROM platform_deployment_profiles
            WHERE id = %s
            RETURNING id
            """,
            (deployment_profile_id.strip(),),
        ).fetchone()
    return row is not None


def upsert_deployment_binding(
    database_url: str,
    *,
    deployment_profile_id: str,
    capability_key: str,
    provider_instance_id: str,
    resources: list[dict[str, Any]] | None = None,
    default_resource_id: str | None = None,
    binding_config: dict[str, Any] | None = None,
    resource_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
                INSERT INTO platform_deployment_bindings (
                    id,
                    deployment_profile_id,
                    capability_key,
                    provider_instance_id,
                    binding_config,
                    resource_policy
                )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
            ON CONFLICT (deployment_profile_id, capability_key)
            DO UPDATE SET
              provider_instance_id = EXCLUDED.provider_instance_id,
              binding_config = EXCLUDED.binding_config,
              resource_policy = EXCLUDED.resource_policy,
              updated_at = NOW()
            RETURNING *
            """,
            (
                str(uuid4()),
                deployment_profile_id.strip(),
                capability_key.strip().lower(),
                provider_instance_id.strip(),
                Jsonb(binding_config or {}),
                Jsonb(resource_policy or {}),
            ),
        ).fetchone()
        if row is not None:
            _replace_binding_resources(
                connection,
                binding_id=str(row["id"]),
                resources=resources or [],
                default_resource_id=default_resource_id.strip() if default_resource_id else None,
            )
    if row is None:
        raise RuntimeError("failed_to_upsert_deployment_binding")
    return dict(row)


def list_deployment_profiles(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
              p.id,
              p.slug,
              p.display_name,
              p.description,
              p.created_by_user_id,
              p.updated_by_user_id,
              p.created_at,
              p.updated_at,
              a.deployment_profile_id IS NOT NULL AS is_active
            FROM platform_deployment_profiles p
            LEFT JOIN platform_active_deployment a
              ON a.singleton_key = 'active' AND a.deployment_profile_id = p.id
            ORDER BY p.created_at ASC, p.slug ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_deployment_profile(database_url: str, deployment_profile_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              p.id,
              p.slug,
              p.display_name,
              p.description,
              p.created_by_user_id,
              p.updated_by_user_id,
              p.created_at,
              p.updated_at,
              a.deployment_profile_id IS NOT NULL AS is_active
            FROM platform_deployment_profiles p
            LEFT JOIN platform_active_deployment a
              ON a.singleton_key = 'active' AND a.deployment_profile_id = p.id
            WHERE p.id = %s
            """,
            (deployment_profile_id.strip(),),
        ).fetchone()
    return dict(row) if row is not None else None


def list_deployment_bindings(database_url: str, *, deployment_profile_id: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
              b.id,
              b.deployment_profile_id,
              b.capability_key,
              b.provider_instance_id,
              b.binding_config,
              b.resource_policy,
              b.created_at,
              b.updated_at,
              i.slug AS provider_slug,
              i.provider_key,
              i.display_name AS provider_display_name,
              i.description AS provider_description,
              i.endpoint_url,
              i.healthcheck_url,
              i.enabled,
              i.config_json,
              f.adapter_kind
            FROM platform_deployment_bindings b
            JOIN platform_provider_instances i ON i.id = b.provider_instance_id
            JOIN platform_provider_families f ON f.provider_key = i.provider_key
            WHERE b.deployment_profile_id = %s
            ORDER BY b.capability_key ASC
            """,
            (deployment_profile_id.strip(),),
        ).fetchall()
        return _attach_resources(connection, [dict(row) for row in rows])


def get_active_deployment(database_url: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              a.singleton_key,
              a.deployment_profile_id,
              a.previous_deployment_profile_id,
              a.activated_by_user_id,
              a.activated_at,
              p.slug,
              p.display_name,
              p.description
            FROM platform_active_deployment a
            JOIN platform_deployment_profiles p ON p.id = a.deployment_profile_id
            WHERE a.singleton_key = 'active'
            """
        ).fetchone()
    return dict(row) if row is not None else None


def get_active_binding_for_capability(database_url: str, *, capability_key: str) -> dict[str, Any] | None:
    normalized_capability = capability_key.strip().lower()
    if normalized_capability not in _CAPABILITIES:
        raise ValueError("invalid_capability")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              b.id,
              b.capability_key,
              b.provider_instance_id,
              b.binding_config,
              b.resource_policy,
              i.slug AS provider_slug,
              i.provider_key,
              i.display_name AS provider_display_name,
              i.description AS provider_description,
              i.endpoint_url,
              i.healthcheck_url,
              i.enabled,
              i.config_json,
              f.adapter_kind,
              p.id AS deployment_profile_id,
              p.slug AS deployment_profile_slug,
              p.display_name AS deployment_profile_display_name
            FROM platform_active_deployment a
            JOIN platform_deployment_profiles p ON p.id = a.deployment_profile_id
            JOIN platform_deployment_bindings b ON b.deployment_profile_id = p.id
            JOIN platform_provider_instances i ON i.id = b.provider_instance_id
            JOIN platform_provider_families f ON f.provider_key = i.provider_key
            WHERE a.singleton_key = 'active' AND b.capability_key = %s
            """,
            (normalized_capability,),
        ).fetchone()
        if row is None:
            return None
        return _attach_resources(connection, [dict(row)])[0]


def get_active_binding_for_provider_instance(database_url: str, *, provider_instance_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              b.id,
              b.capability_key,
              b.provider_instance_id,
              b.binding_config,
              b.resource_policy,
              i.slug AS provider_slug,
              i.provider_key,
              i.display_name AS provider_display_name,
              i.description AS provider_description,
              i.endpoint_url,
              i.healthcheck_url,
              i.enabled,
              i.config_json,
              f.adapter_kind,
              p.id AS deployment_profile_id,
              p.slug AS deployment_profile_slug,
              p.display_name AS deployment_profile_display_name
            FROM platform_active_deployment a
            JOIN platform_deployment_profiles p ON p.id = a.deployment_profile_id
            JOIN platform_deployment_bindings b ON b.deployment_profile_id = p.id
            JOIN platform_provider_instances i ON i.id = b.provider_instance_id
            JOIN platform_provider_families f ON f.provider_key = i.provider_key
            WHERE a.singleton_key = 'active' AND b.provider_instance_id = %s
            """,
            (provider_instance_id.strip(),),
        ).fetchone()
        if row is None:
            return None
        return _attach_resources(connection, [dict(row)])[0]


def _replace_binding_resources(
    connection: Any,
    *,
    binding_id: str,
    resources: list[dict[str, Any]],
    default_resource_id: str | None,
) -> None:
    connection.execute(
        """
        DELETE FROM platform_binding_resources
        WHERE binding_id = %s
        """,
        (binding_id,),
    )
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            continue
        resource_id = str(
            resource.get("id")
            or resource.get("managed_model_id")
            or resource.get("knowledge_base_id")
            or resource.get("provider_resource_id")
            or ""
        ).strip()
        if not resource_id:
            continue
        managed_model_id = str(resource.get("managed_model_id") or "").strip() or None
        knowledge_base_id = str(resource.get("knowledge_base_id") or "").strip() or None
        provider_resource_id = str(resource.get("provider_resource_id") or "").strip() or None
        connection.execute(
            """
            INSERT INTO platform_binding_resources (
                binding_id,
                resource_id,
                resource_kind,
                ref_type,
                managed_model_id,
                knowledge_base_id,
                provider_resource_id,
                display_name,
                metadata_json,
                is_default,
                sort_order
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                binding_id,
                resource_id,
                str(resource.get("resource_kind") or "").strip().lower(),
                str(resource.get("ref_type") or "").strip().lower(),
                managed_model_id,
                knowledge_base_id,
                provider_resource_id,
                str(resource.get("display_name") or "").strip() or None,
                Jsonb(resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}),
                resource_id == (default_resource_id or ""),
                index,
            ),
        )


def _attach_resources(connection: Any, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    binding_ids = [str(row.get("id") or "").strip() for row in rows if str(row.get("id") or "").strip()]
    if not binding_ids:
        return rows
    resource_rows = connection.execute(
        """
        SELECT
          br.binding_id,
          br.resource_id,
          br.resource_kind,
          br.ref_type,
          br.managed_model_id,
          br.knowledge_base_id,
          br.provider_resource_id,
          br.display_name,
          br.metadata_json,
          br.is_default,
          br.sort_order,
          m.name AS model_name,
          m.provider AS model_provider,
          m.backend_kind AS model_backend_kind,
          m.task_key AS model_task_key,
          m.provider_model_id AS model_provider_model_id,
          m.local_path AS model_local_path,
          m.source_id AS model_source_id,
          m.availability AS model_availability,
          kb.slug AS knowledge_base_slug,
          kb.display_name AS knowledge_base_display_name,
          kb.index_name AS knowledge_base_index_name,
          kb.lifecycle_state AS knowledge_base_lifecycle_state,
          kb.sync_status AS knowledge_base_sync_status,
          kb.document_count AS knowledge_base_document_count
        FROM platform_binding_resources br
        LEFT JOIN model_registry m ON m.model_id = br.managed_model_id
        LEFT JOIN context_knowledge_bases kb ON kb.id = br.knowledge_base_id
        WHERE br.binding_id = ANY(%s)
        ORDER BY br.binding_id ASC, br.sort_order ASC, br.resource_id ASC
        """,
        (binding_ids,),
    ).fetchall()
    resources_by_binding: dict[str, list[dict[str, Any]]] = {}
    for raw in resource_rows:
        row = dict(raw)
        binding_id = str(row["binding_id"])
        metadata = dict(row.get("metadata_json") or {})
        if str(row.get("resource_kind") or "").strip().lower() == "model":
            metadata = {
                **metadata,
                "name": row.get("model_name") or metadata.get("name"),
                "provider": row.get("model_provider") or metadata.get("provider"),
                "backend": row.get("model_backend_kind") or metadata.get("backend"),
                "task_key": row.get("model_task_key") or metadata.get("task_key"),
                "provider_model_id": row.get("model_provider_model_id") or metadata.get("provider_model_id"),
                "local_path": row.get("model_local_path") or metadata.get("local_path"),
                "source_id": row.get("model_source_id") or metadata.get("source_id"),
                "availability": row.get("model_availability") or metadata.get("availability"),
            }
        if str(row.get("ref_type") or "").strip().lower() == "knowledge_base":
            metadata = {
                **metadata,
                "slug": row.get("knowledge_base_slug") or metadata.get("slug"),
                "name": row.get("knowledge_base_display_name") or metadata.get("name"),
                "index_name": row.get("knowledge_base_index_name") or metadata.get("index_name"),
                "lifecycle_state": row.get("knowledge_base_lifecycle_state") or metadata.get("lifecycle_state"),
                "sync_status": row.get("knowledge_base_sync_status") or metadata.get("sync_status"),
                "document_count": row.get("knowledge_base_document_count") if row.get("knowledge_base_document_count") is not None else metadata.get("document_count"),
            }
        resources_by_binding.setdefault(binding_id, []).append(
            {
                "id": str(row["resource_id"]),
                "resource_kind": str(row.get("resource_kind") or "").strip().lower(),
                "ref_type": str(row.get("ref_type") or "").strip().lower(),
                "managed_model_id": str(row.get("managed_model_id") or "").strip() or None,
                "knowledge_base_id": str(row.get("knowledge_base_id") or "").strip() or None,
                "provider_resource_id": str(row.get("provider_resource_id") or "").strip() or None,
                "display_name": row.get("display_name") or row.get("model_name"),
                "metadata": metadata,
                "is_default": bool(row.get("is_default")),
                "sort_order": int(row.get("sort_order") or 0),
            }
        )
    for row in rows:
        binding_id = str(row.get("id") or "").strip()
        resources = resources_by_binding.get(binding_id, [])
        default_resource = next((dict(item) for item in resources if bool(item.get("is_default"))), None)
        row["resources"] = [dict(item) for item in resources]
        row["default_resource"] = default_resource
        row["default_resource_id"] = (
            str(default_resource.get("id", "")).strip() if isinstance(default_resource, dict) else None
        ) or None
    return rows


def activate_deployment_profile(
    database_url: str,
    *,
    deployment_profile_id: str,
    activated_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        current = connection.execute(
            """
            SELECT deployment_profile_id
            FROM platform_active_deployment
            WHERE singleton_key = 'active'
            """
        ).fetchone()
        previous_id = str(current["deployment_profile_id"]) if current is not None else None
        row = connection.execute(
            """
            INSERT INTO platform_active_deployment (
                singleton_key,
                deployment_profile_id,
                previous_deployment_profile_id,
                activated_by_user_id,
                activated_at
            )
            VALUES ('active', %s, %s, %s, NOW())
            ON CONFLICT (singleton_key)
            DO UPDATE SET
              deployment_profile_id = EXCLUDED.deployment_profile_id,
              previous_deployment_profile_id = EXCLUDED.previous_deployment_profile_id,
              activated_by_user_id = EXCLUDED.activated_by_user_id,
              activated_at = EXCLUDED.activated_at
            RETURNING *
            """,
            (
                deployment_profile_id.strip(),
                previous_id,
                activated_by_user_id,
            ),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO platform_deployment_activation_audit (
                id,
                deployment_profile_id,
                previous_deployment_profile_id,
                activated_by_user_id,
                activated_at
            )
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (
                str(uuid4()),
                deployment_profile_id.strip(),
                previous_id,
                activated_by_user_id,
            ),
        )
    if row is None:
        raise RuntimeError("failed_to_activate_deployment_profile")
    return dict(row)


def list_deployment_activation_audit(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
              a.id,
              a.deployment_profile_id,
              current_profile.slug AS deployment_profile_slug,
              current_profile.display_name AS deployment_profile_display_name,
              a.previous_deployment_profile_id,
              previous_profile.slug AS previous_deployment_profile_slug,
              previous_profile.display_name AS previous_deployment_profile_display_name,
              a.activated_by_user_id,
              a.activated_at
            FROM platform_deployment_activation_audit a
            JOIN platform_deployment_profiles current_profile ON current_profile.id = a.deployment_profile_id
            LEFT JOIN platform_deployment_profiles previous_profile ON previous_profile.id = a.previous_deployment_profile_id
            ORDER BY a.activated_at DESC, a.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]
