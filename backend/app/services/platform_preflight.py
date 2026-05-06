from __future__ import annotations

from typing import Any

from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
)


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _health_reachable(validation: dict[str, Any]) -> bool | None:
    health = validation.get("health") if isinstance(validation.get("health"), dict) else {}
    return _bool_or_none(health.get("reachable"))


def _operation_reachable(capability_key: str, validation: dict[str, Any]) -> bool | None:
    if capability_key == CAPABILITY_LLM_INFERENCE:
        return _bool_or_none(validation.get("resources_reachable"))
    if capability_key == CAPABILITY_EMBEDDINGS:
        return _bool_or_none(validation.get("embeddings_reachable"))
    if capability_key == CAPABILITY_VECTOR_STORE:
        return _bool_or_none(validation.get("resources_reachable"))
    if capability_key == CAPABILITY_SANDBOX_EXECUTION:
        return _bool_or_none(validation.get("execute_reachable"))
    if capability_key == CAPABILITY_MCP_RUNTIME:
        return _bool_or_none(validation.get("invoke_reachable"))
    return _health_reachable(validation)


def _operation_failure_code(capability_key: str) -> str:
    if capability_key == CAPABILITY_EMBEDDINGS:
        return "embeddings_unreachable"
    if capability_key == CAPABILITY_SANDBOX_EXECUTION:
        return "execute_unreachable"
    if capability_key == CAPABILITY_MCP_RUNTIME:
        return "invoke_unreachable"
    return "resources_unreachable"


def _operation_failure_message(capability_key: str, validation: dict[str, Any]) -> str:
    if capability_key == CAPABILITY_EMBEDDINGS:
        status = validation.get("embeddings_status_code")
        return f"Embeddings request failed with HTTP {status}" if status else "Embeddings request failed"
    if capability_key == CAPABILITY_SANDBOX_EXECUTION:
        status = validation.get("execute_status_code")
        return f"Sandbox dry run failed with HTTP {status}" if status else "Sandbox dry run failed"
    if capability_key == CAPABILITY_MCP_RUNTIME:
        status = validation.get("invoke_status_code")
        return f"MCP health tool invocation failed with HTTP {status}" if status else "MCP health tool invocation failed"
    status = validation.get("resources_status_code")
    return f"Provider resources could not be listed with HTTP {status}" if status else "Provider resources could not be listed"


def _discovery_reachable(validation: dict[str, Any]) -> bool | None:
    resources_reachable = _bool_or_none(validation.get("resources_reachable"))
    if resources_reachable is not None:
        return resources_reachable
    return _health_reachable(validation)


def _blocking_resource_failures(
    validation: dict[str, Any],
    *,
    non_blocking_resource_errors: set[str],
) -> list[dict[str, Any]]:
    resource_errors = validation.get("resource_errors")
    if not isinstance(resource_errors, list):
        return []
    failures: list[dict[str, Any]] = []
    for item in resource_errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        if code and code in non_blocking_resource_errors:
            continue
        failures.append(
            {
                "code": code or "resource_error",
                "message": "Bound resource is not exposed by the selected provider",
                **dict(item),
            }
        )
    return failures


def _binding_failure(
    validation: dict[str, Any],
    *,
    non_blocking_binding_errors: set[str],
) -> dict[str, Any] | None:
    binding_error = str(validation.get("binding_error") or "").strip()
    if not binding_error or binding_error in non_blocking_binding_errors:
        return None
    return {
        "code": binding_error,
        "message": "Provider binding is incomplete or invalid",
    }


def _blocking_failures(
    capability_key: str,
    validation: dict[str, Any],
    *,
    non_blocking_binding_errors: set[str],
    non_blocking_resource_errors: set[str],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    binding_failure = _binding_failure(
        validation,
        non_blocking_binding_errors=non_blocking_binding_errors,
    )
    if binding_failure:
        failures.append(binding_failure)

    operation_reachable = _operation_reachable(capability_key, validation)
    if operation_reachable is False:
        failures.append(
            {
                "code": _operation_failure_code(capability_key),
                "message": _operation_failure_message(capability_key, validation),
            }
        )

    failures.extend(
        _blocking_resource_failures(
            validation,
            non_blocking_resource_errors=non_blocking_resource_errors,
        )
    )
    return failures


def _annotate_provider_validation(
    capability_key: str,
    validation: dict[str, Any],
    *,
    non_blocking_binding_errors: set[str] | None = None,
    non_blocking_resource_errors: set[str] | None = None,
) -> dict[str, Any]:
    normalized_capability = str(capability_key or "").strip().lower()
    annotated = dict(validation)
    annotated["diagnostic_health_reachable"] = _health_reachable(annotated)
    annotated["discovery_reachable"] = _discovery_reachable(annotated)
    annotated["operation_reachable"] = _operation_reachable(normalized_capability, annotated)
    annotated["blocking_failures"] = _blocking_failures(
        normalized_capability,
        annotated,
        non_blocking_binding_errors=non_blocking_binding_errors or set(),
        non_blocking_resource_errors=non_blocking_resource_errors or set(),
    )
    return annotated
