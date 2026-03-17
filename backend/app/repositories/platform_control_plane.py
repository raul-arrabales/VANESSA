from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from ..db import get_connection

_CAPABILITIES = {"llm_inference", "vector_store"}


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
                    str(uuid4()),
                    str(profile_row["id"]),
                    str(binding["capability_key"]).strip().lower(),
                    str(binding["provider_instance_id"]).strip(),
                    Jsonb(binding.get("binding_config") or {}),
                ),
            )
    return get_deployment_profile(database_url, str(profile_row["id"])) or {}


def upsert_deployment_binding(
    database_url: str,
    *,
    deployment_profile_id: str,
    capability_key: str,
    provider_instance_id: str,
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
    return [dict(row) for row in rows]


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
    return dict(row) if row is not None else None


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
