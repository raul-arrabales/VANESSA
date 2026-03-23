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


def count_deployment_bindings_for_served_model(database_url: str, *, model_id: str) -> int:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS binding_count
            FROM platform_binding_served_models
            WHERE model_id = %s
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
                    binding_config
                )
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    binding_id,
                    str(profile_row["id"]),
                    str(binding["capability_key"]).strip().lower(),
                    str(binding["provider_instance_id"]).strip(),
                    Jsonb(binding.get("binding_config") or {}),
                ),
            )
            _replace_binding_served_models(
                connection,
                binding_id=binding_id,
                served_model_ids=binding.get("served_model_ids") or [],
                default_served_model_id=str(binding.get("default_served_model_id") or "").strip() or None,
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
                    binding_config
                )
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    binding_id,
                    deployment_profile_id.strip(),
                    str(binding["capability_key"]).strip().lower(),
                    str(binding["provider_instance_id"]).strip(),
                    Jsonb(binding.get("binding_config") or {}),
                ),
            )
            _replace_binding_served_models(
                connection,
                binding_id=binding_id,
                served_model_ids=binding.get("served_model_ids") or [],
                default_served_model_id=str(binding.get("default_served_model_id") or "").strip() or None,
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
    served_model_ids: list[str] | None = None,
    default_served_model_id: str | None = None,
    binding_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO platform_deployment_bindings (
                id,
                deployment_profile_id,
                capability_key,
                provider_instance_id,
                binding_config
            )
            VALUES (%s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (deployment_profile_id, capability_key)
            DO UPDATE SET
              provider_instance_id = EXCLUDED.provider_instance_id,
              binding_config = EXCLUDED.binding_config,
              updated_at = NOW()
            RETURNING *
            """,
            (
                str(uuid4()),
                deployment_profile_id.strip(),
                capability_key.strip().lower(),
                provider_instance_id.strip(),
                Jsonb(binding_config or {}),
            ),
        ).fetchone()
        if row is not None:
            _replace_binding_served_models(
                connection,
                binding_id=str(row["id"]),
                served_model_ids=served_model_ids or [],
                default_served_model_id=default_served_model_id.strip() if default_served_model_id else None,
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
        return _attach_served_models(connection, [dict(row) for row in rows])


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
        return _attach_served_models(connection, [dict(row)])[0]


def get_active_binding_for_provider_instance(database_url: str, *, provider_instance_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
              b.id,
              b.capability_key,
              b.provider_instance_id,
              b.binding_config,
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
        return _attach_served_models(connection, [dict(row)])[0]


def _replace_binding_served_models(
    connection: Any,
    *,
    binding_id: str,
    served_model_ids: list[str],
    default_served_model_id: str | None,
) -> None:
    connection.execute(
        """
        DELETE FROM platform_binding_served_models
        WHERE binding_id = %s
        """,
        (binding_id,),
    )
    for index, model_id in enumerate(served_model_ids):
        normalized_model_id = str(model_id).strip()
        if not normalized_model_id:
            continue
        connection.execute(
            """
            INSERT INTO platform_binding_served_models (
                binding_id,
                model_id,
                is_default,
                sort_order
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                binding_id,
                normalized_model_id,
                normalized_model_id == (default_served_model_id or ""),
                index,
            ),
        )


def _attach_served_models(connection: Any, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    binding_ids = [str(row.get("id") or "").strip() for row in rows if str(row.get("id") or "").strip()]
    if not binding_ids:
        return rows
    served_rows = connection.execute(
        """
        SELECT
          bsm.binding_id,
          bsm.model_id,
          bsm.is_default,
          bsm.sort_order,
          m.name AS model_name,
          m.provider AS model_provider,
          m.backend_kind AS model_backend_kind,
          m.task_key AS model_task_key,
          m.provider_model_id AS model_provider_model_id,
          m.local_path AS model_local_path,
          m.source_id AS model_source_id,
          m.availability AS model_availability
        FROM platform_binding_served_models bsm
        JOIN model_registry m ON m.model_id = bsm.model_id
        WHERE bsm.binding_id = ANY(%s)
        ORDER BY bsm.binding_id ASC, bsm.sort_order ASC, bsm.model_id ASC
        """,
        (binding_ids,),
    ).fetchall()
    served_by_binding: dict[str, list[dict[str, Any]]] = {}
    for raw in served_rows:
        row = dict(raw)
        binding_id = str(row["binding_id"])
        served_by_binding.setdefault(binding_id, []).append(
            {
                "id": str(row["model_id"]),
                "name": row.get("model_name"),
                "provider": row.get("model_provider"),
                "backend": row.get("model_backend_kind"),
                "task_key": row.get("model_task_key"),
                "provider_model_id": row.get("model_provider_model_id"),
                "local_path": row.get("model_local_path"),
                "source_id": row.get("model_source_id"),
                "availability": row.get("model_availability"),
                "is_default": bool(row.get("is_default")),
                "sort_order": int(row.get("sort_order") or 0),
            }
        )
    for row in rows:
        binding_id = str(row.get("id") or "").strip()
        served_models = served_by_binding.get(binding_id, [])
        default_served_model = next((dict(item) for item in served_models if bool(item.get("is_default"))), None)
        row["served_models"] = [dict(item) for item in served_models]
        row["default_served_model"] = default_served_model
        row["default_served_model_id"] = (
            str(default_served_model.get("id", "")).strip() if isinstance(default_served_model, dict) else None
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
