from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..repositories import context_management as context_repo
from .platform_resources import _runtime_identifier_for_resource
from .platform_serialization import _serialize_deployment_profile
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_VECTOR_STORE,
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


def _binding_rows_by_capability(bindings: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(binding.get("capability_key") or binding.get("capability") or "").strip().lower(): binding
        for binding in bindings
        if isinstance(binding, dict) and str(binding.get("capability_key") or binding.get("capability") or "").strip()
    }


def _binding_configuration_status(
    database_url: str,
    *,
    binding: dict[str, Any],
    bindings_by_capability: dict[str, dict[str, Any]],
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
        provider_origin = str(binding.get("provider_origin") or "local").strip().lower()
        for resource in resources:
            metadata = dict(resource.get("metadata") or {})
            backend = str(metadata.get("backend") or "").strip().lower()
            if provider_origin == "cloud" and backend and backend != "external_api":
                issues.append(
                    _issue(
                        "resource_provider_origin_mismatch",
                        f"{resource.get('display_name') or resource.get('id') or 'Selected model'} is local and cannot be served by a cloud provider.",
                    )
                )
            elif provider_origin != "cloud" and backend and backend != "local":
                issues.append(
                    _issue(
                        "resource_provider_origin_mismatch",
                        f"{resource.get('display_name') or resource.get('id') or 'Selected model'} is cloud-hosted and cannot be served by a local provider.",
                    )
                )
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


def compute_deployment_configuration_status(
    database_url: str,
    *,
    bindings: list[dict[str, Any]],
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


def serialize_deployment_profile_with_status(
    database_url: str,
    profile: dict[str, Any],
    bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    serialized = _serialize_deployment_profile(profile, bindings)
    binding_statuses, deployment_status = compute_deployment_configuration_status(database_url, bindings=bindings)
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
