from __future__ import annotations

from ..config import AuthConfig
from ..repositories import platform_control_plane as platform_repo
from .platform_bindings import _coerce_create_input, _resolve_deployment_bindings, _validate_deployment_profile_bindings
from .platform_bootstrap import ensure_platform_bootstrap_state
from .platform_serialization import _serialize_activation_audit_row, _serialize_deployment_profile
from .platform_types import PlatformControlPlaneError, REQUIRED_CAPABILITIES


def list_deployment_profiles(database_url: str, config: AuthConfig) -> list[dict[str, object]]:
    ensure_platform_bootstrap_state(database_url, config)
    items: list[dict[str, object]] = []
    for profile in platform_repo.list_deployment_profiles(database_url):
        bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(profile["id"]))
        items.append(_serialize_deployment_profile(profile, bindings))
    return items


def list_deployment_activation_audit(database_url: str, config: AuthConfig) -> list[dict[str, object]]:
    ensure_platform_bootstrap_state(database_url, config)
    return [_serialize_activation_audit_row(row) for row in platform_repo.list_deployment_activation_audit(database_url)]


def create_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    payload: dict[str, object],
    created_by_user_id: int,
) -> dict[str, object]:
    ensure_platform_bootstrap_state(database_url, config)
    normalized = _coerce_create_input(database_url, payload)
    resolved_bindings = _resolve_deployment_bindings(database_url, normalized.bindings)
    try:
        created = platform_repo.create_deployment_profile(
            database_url,
            slug=normalized.slug,
            display_name=normalized.display_name,
            description=normalized.description,
            bindings=resolved_bindings,
            created_by_user_id=created_by_user_id,
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "deployment_profile_exists",
                "Deployment profile slug already exists",
                status_code=409,
            ) from exc
        raise
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(created["id"]))
    return _serialize_deployment_profile(created, bindings)


def update_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    deployment_profile_id: str,
    payload: dict[str, object],
    updated_by_user_id: int,
) -> dict[str, object]:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if existing is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    normalized = _coerce_create_input(database_url, payload)
    resolved_bindings = _resolve_deployment_bindings(database_url, normalized.bindings)
    try:
        updated = platform_repo.update_deployment_profile(
            database_url,
            deployment_profile_id=deployment_profile_id,
            slug=normalized.slug,
            display_name=normalized.display_name,
            description=normalized.description,
            bindings=resolved_bindings,
            updated_by_user_id=updated_by_user_id,
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "deployment_profile_exists",
                "Deployment profile slug already exists",
                status_code=409,
            ) from exc
        raise
    if updated is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    return _serialize_deployment_profile(updated, bindings)


def clone_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    source_deployment_profile_id: str,
    payload: dict[str, object],
    created_by_user_id: int,
) -> dict[str, object]:
    ensure_platform_bootstrap_state(database_url, config)
    source = platform_repo.get_deployment_profile(database_url, source_deployment_profile_id)
    if source is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    source_bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=source_deployment_profile_id)
    if not source_bindings:
        raise PlatformControlPlaneError(
            "deployment_profile_incomplete",
            "Deployment profile is missing required capability bindings",
            status_code=409,
        )
    slug = str(payload.get("slug", "")).strip().lower()
    display_name = str(payload.get("display_name", "")).strip()
    description = str(payload.get("description", source.get("description", ""))).strip()
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    try:
        created = platform_repo.create_deployment_profile(
            database_url,
            slug=slug,
            display_name=display_name,
            description=description,
            bindings=[
                {
                    "capability_key": str(binding["capability_key"]).strip().lower(),
                    "provider_instance_id": str(binding["provider_instance_id"]).strip(),
                    "resources": [dict(resource) for resource in (binding.get("resources") or []) if isinstance(resource, dict)],
                    "default_resource_id": str(binding.get("default_resource_id") or "").strip() or None,
                    "binding_config": dict(binding.get("binding_config") or {}),
                    "resource_policy": dict(binding.get("resource_policy") or {}),
                }
                for binding in source_bindings
            ],
            created_by_user_id=created_by_user_id,
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "deployment_profile_exists",
                "Deployment profile slug already exists",
                status_code=409,
            ) from exc
        raise
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(created["id"]))
    return _serialize_deployment_profile(created, bindings)


def delete_deployment_profile(database_url: str, *, config: AuthConfig, deployment_profile_id: str) -> None:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if existing is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    if bool(existing.get("is_active")):
        raise PlatformControlPlaneError(
            "deployment_profile_active",
            "Active deployment profile cannot be deleted",
            status_code=409,
        )
    deleted = platform_repo.delete_deployment_profile(database_url, deployment_profile_id)
    if not deleted:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)


def activate_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    deployment_profile_id: str,
    activated_by_user_id: int,
) -> dict[str, object]:
    ensure_platform_bootstrap_state(database_url, config)
    profile = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if profile is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    bound_capabilities = {str(binding["capability_key"]).strip().lower() for binding in bindings}
    missing_capabilities = sorted(REQUIRED_CAPABILITIES - bound_capabilities)
    if missing_capabilities:
        raise PlatformControlPlaneError(
            "deployment_profile_incomplete",
            "Deployment profile is missing required capability bindings",
            status_code=409,
            details={"missing_capabilities": missing_capabilities},
        )
    for binding in bindings:
        if not bool(binding.get("enabled", True)):
            raise PlatformControlPlaneError(
                "deployment_profile_disabled_provider",
                "Deployment profile references a disabled provider instance",
                status_code=409,
                details={"provider_instance_id": str(binding["provider_instance_id"])},
            )
    validation_failures = _validate_deployment_profile_bindings(database_url, config, bindings)
    if validation_failures:
        raise PlatformControlPlaneError(
            "deployment_profile_validation_failed",
            "Deployment profile preflight validation failed",
            status_code=409,
            details={"providers": validation_failures},
        )
    platform_repo.activate_deployment_profile(
        database_url,
        deployment_profile_id=deployment_profile_id,
        activated_by_user_id=activated_by_user_id,
    )
    refreshed = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    refreshed_bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    if refreshed is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    return _serialize_deployment_profile(refreshed, refreshed_bindings)
