from __future__ import annotations

from collections.abc import Iterable

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from ..repositories import platform_control_plane as platform_repo
from .platform_bindings import (
    _coerce_binding_input,
    _coerce_create_input,
    _require_complete_provider_binding_set,
    _resolve_deployment_bindings,
    _validate_deployment_profile_bindings,
)
from .platform_bootstrap import ensure_platform_bootstrap_state
from .platform_serialization import _runtime_identifier_for_resource, _serialize_activation_audit_row, _serialize_deployment_profile
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_VECTOR_STORE,
    PlatformControlPlaneError,
    REQUIRED_CAPABILITIES,
)


def _describe_capability(capability_key: str) -> str:
    labels = {
        CAPABILITY_LLM_INFERENCE: "LLM inference",
        CAPABILITY_EMBEDDINGS: "Embeddings",
        CAPABILITY_VECTOR_STORE: "Vector store",
    }
    return labels.get(capability_key, capability_key)


def _issue(code: str, message: str) -> dict[str, object]:
    return {
        "code": code,
        "message": message,
    }


def _binding_rows_by_capability(bindings: Iterable[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {
        str(binding.get("capability_key") or binding.get("capability") or "").strip().lower(): binding
        for binding in bindings
        if isinstance(binding, dict) and str(binding.get("capability_key") or binding.get("capability") or "").strip()
    }


def _binding_configuration_status(
    database_url: str,
    *,
    binding: dict[str, object],
    bindings_by_capability: dict[str, dict[str, object]],
) -> dict[str, object]:
    capability_key = str(binding.get("capability_key") or binding.get("capability") or "").strip().lower()
    issues: list[dict[str, object]] = []
    if not bool(binding.get("enabled", True)):
        issues.append(_issue("provider_disabled", "Selected provider is disabled."))

    resources = [dict(item) for item in (binding.get("resources") or []) if isinstance(item, dict)]
    default_resource_id = str(binding.get("default_resource_id") or "").strip() or None

    if capability_key in {CAPABILITY_LLM_INFERENCE, CAPABILITY_EMBEDDINGS}:
        if not resources:
            issues.append(_issue("resources_missing", "At least one model resource must be bound."))
        elif not default_resource_id:
            issues.append(_issue("default_resource_missing", "Select a default model resource."))
    elif capability_key == CAPABILITY_VECTOR_STORE:
        resource_policy = dict(binding.get("resource_policy") or {})
        selection_mode = str(resource_policy.get("selection_mode") or "explicit").strip().lower()
        if selection_mode == "dynamic_namespace":
            if not str(resource_policy.get("namespace_prefix") or "").strip():
                issues.append(_issue("namespace_prefix_missing", "Dynamic namespace mode requires a namespace prefix."))
        elif not resources:
            issues.append(_issue("resources_missing", "At least one knowledge base must be bound in explicit mode."))

        embeddings_binding = bindings_by_capability.get(CAPABILITY_EMBEDDINGS)
        embeddings_provider_id = str((embeddings_binding or {}).get("provider_instance_id") or "").strip()
        embeddings_default_resource_id = _runtime_identifier_for_resource(
            next(
                (
                    resource
                    for resource in (embeddings_binding or {}).get("resources") or []
                    if isinstance(resource, dict)
                    and str(resource.get("id") or "").strip()
                    == str((embeddings_binding or {}).get("default_resource_id") or "").strip()
                ),
                {},
            )
        ) or None
        for resource in resources:
            knowledge_base_id = str(resource.get("knowledge_base_id") or "").strip()
            if not knowledge_base_id:
                continue
            knowledge_base = context_repo.get_knowledge_base(database_url, knowledge_base_id)
            if knowledge_base is None:
                continue
            vectorization_mode = str(knowledge_base.get("vectorization_mode") or "").strip().lower()
            if vectorization_mode == "self_provided":
                issues.append(
                    _issue(
                        "knowledge_base_self_provided_unsupported",
                        f"{knowledge_base.get('display_name') or knowledge_base_id} expects self-provided vectors and is not usable through deployment retrieval yet.",
                    )
                )
                continue
            knowledge_base_embeddings_provider_id = str(knowledge_base.get("embedding_provider_instance_id") or "").strip()
            knowledge_base_embeddings_resource_id = str(knowledge_base.get("embedding_resource_id") or "").strip()
            if not embeddings_provider_id:
                issues.append(
                    _issue(
                        "embeddings_binding_missing_resources",
                        "Embeddings must have a default model before this knowledge base can be used.",
                    )
                )
                continue
            if knowledge_base_embeddings_provider_id != embeddings_provider_id:
                issues.append(
                    _issue(
                        "knowledge_base_embeddings_provider_mismatch",
                        f"{knowledge_base.get('display_name') or knowledge_base_id} targets a different embeddings provider.",
                    )
                )
            if not embeddings_default_resource_id:
                issues.append(
                    _issue(
                        "embeddings_default_missing",
                        "Embeddings must have a default model before this knowledge base can be used.",
                    )
                )
            elif knowledge_base_embeddings_resource_id != embeddings_default_resource_id:
                issues.append(
                    _issue(
                        "knowledge_base_embeddings_resource_mismatch",
                        f"{knowledge_base.get('display_name') or knowledge_base_id} targets a different embeddings model.",
                    )
                )

    deduped_issues: list[dict[str, object]] = []
    seen_issue_keys: set[tuple[str, str]] = set()
    for issue in issues:
        issue_key = (str(issue.get("code") or ""), str(issue.get("message") or ""))
        if issue_key in seen_issue_keys:
            continue
        seen_issue_keys.add(issue_key)
        deduped_issues.append(issue)
    is_ready = len(deduped_issues) == 0
    summary = "Ready." if is_ready else str(deduped_issues[0]["message"])
    return {
        "is_ready": is_ready,
        "issues": deduped_issues,
        "summary": summary,
    }


def _deployment_configuration_status(
    database_url: str,
    *,
    bindings: list[dict[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    bindings_by_capability = _binding_rows_by_capability(bindings)
    binding_statuses = {
        capability_key: _binding_configuration_status(
            database_url,
            binding=binding,
            bindings_by_capability=bindings_by_capability,
        )
        for capability_key, binding in bindings_by_capability.items()
    }
    incomplete_capabilities = sorted(
        capability_key
        for capability_key in REQUIRED_CAPABILITIES
        if capability_key not in binding_statuses or not bool(binding_statuses[capability_key].get("is_ready"))
    )
    if not incomplete_capabilities:
        summary = "All required capabilities are configured."
    elif len(incomplete_capabilities) == 1:
        summary = f"{_describe_capability(incomplete_capabilities[0])} is not fully configured."
    else:
        summary = f"{len(incomplete_capabilities)} required capabilities are not fully configured."
    return binding_statuses, {
        "is_ready": len(incomplete_capabilities) == 0,
        "incomplete_capabilities": incomplete_capabilities,
        "summary": summary,
    }


def _serialize_deployment_profile_with_status(
    database_url: str,
    profile: dict[str, object],
    bindings: list[dict[str, object]],
) -> dict[str, object]:
    serialized = _serialize_deployment_profile(profile, bindings)
    binding_statuses, deployment_status = _deployment_configuration_status(database_url, bindings=bindings)
    serialized["bindings"] = [
        {
            **binding,
            "configuration_status": dict(
                binding_statuses.get(str(binding.get("capability") or "").strip().lower())
                or {"is_ready": False, "issues": [], "summary": "Binding is not configured."}
            ),
        }
        for binding in serialized["bindings"]
    ]
    serialized["configuration_status"] = deployment_status
    return serialized


def list_deployment_profiles(database_url: str, config: AuthConfig) -> list[dict[str, object]]:
    ensure_platform_bootstrap_state(database_url, config)
    items: list[dict[str, object]] = []
    for profile in platform_repo.list_deployment_profiles(database_url):
        bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(profile["id"]))
        items.append(_serialize_deployment_profile_with_status(database_url, profile, bindings))
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
    _require_complete_provider_binding_set(resolved_bindings)
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
    return _serialize_deployment_profile_with_status(database_url, created, bindings)


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
    _require_complete_provider_binding_set(resolved_bindings)
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
    return _serialize_deployment_profile_with_status(database_url, updated, bindings)


def update_deployment_profile_identity(
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
    slug = str(payload.get("slug", existing.get("slug", ""))).strip().lower()
    display_name = str(payload.get("display_name", existing.get("display_name", ""))).strip()
    description = str(payload.get("description", existing.get("description", ""))).strip()
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    try:
        updated = platform_repo.update_deployment_profile_identity(
            database_url,
            deployment_profile_id=deployment_profile_id,
            slug=slug,
            display_name=display_name,
            description=description,
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
    return _serialize_deployment_profile_with_status(database_url, updated, bindings)


def upsert_deployment_profile_binding(
    database_url: str,
    *,
    config: AuthConfig,
    deployment_profile_id: str,
    capability_key: str,
    payload: dict[str, object],
    updated_by_user_id: int,
) -> dict[str, object]:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if existing is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    normalized_binding = _coerce_binding_input(
        database_url,
        item=payload,
        capability_key=capability_key,
    )
    resolved_bindings = _resolve_deployment_bindings(database_url, [normalized_binding])
    resolved_binding = resolved_bindings[0]
    platform_repo.upsert_deployment_binding(
        database_url,
        deployment_profile_id=deployment_profile_id,
        capability_key=str(resolved_binding["capability_key"]),
        provider_instance_id=str(resolved_binding["provider_instance_id"]),
        resources=[dict(resource) for resource in resolved_binding.get("resources") or [] if isinstance(resource, dict)],
        default_resource_id=str(resolved_binding.get("default_resource_id") or "").strip() or None,
        binding_config=dict(resolved_binding.get("binding_config") or {}),
        resource_policy=dict(resolved_binding.get("resource_policy") or {}),
    )
    updated = platform_repo.update_deployment_profile_identity(
        database_url,
        deployment_profile_id=deployment_profile_id,
        slug=str(existing.get("slug") or ""),
        display_name=str(existing.get("display_name") or ""),
        description=str(existing.get("description") or ""),
        updated_by_user_id=updated_by_user_id,
    )
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    return _serialize_deployment_profile_with_status(database_url, updated or existing, bindings)


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
    return _serialize_deployment_profile_with_status(database_url, created, bindings)


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
    return _serialize_deployment_profile_with_status(database_url, refreshed, refreshed_bindings)
