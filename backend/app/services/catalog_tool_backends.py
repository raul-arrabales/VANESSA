from __future__ import annotations

import re
from typing import Any

from .catalog_errors import CatalogError
from .context_management_retrieval_schema import (
    DEFAULT_RETRIEVAL_OPTIONS,
    build_knowledge_base_retrieval_input_schema,
    build_knowledge_base_retrieval_output_schema,
)
from .context_management_runtime import list_active_runtime_knowledge_bases, query_knowledge_base
from .image_analysis_tasks import (
    IMAGE_ANALYSIS_TASKS,
    available_tasks_from_resources,
)
from .image_analysis_service import require_image_analysis_task_defaults
from .platform_adapters import http_json_request
from .platform_service import get_active_platform_runtime, resolve_image_analysis_adapter, resolve_mcp_runtime_adapter, resolve_sandbox_execution_adapter
from .platform_types import PlatformControlPlaneError

TOOL_BACKEND_SANDBOX = "sandbox_python"
TOOL_BACKEND_WEB_SEARCH = "mcp_gateway_web_search"
TOOL_BACKEND_INTERNAL_HTTP = "internal_http"
TOOL_BACKEND_KB_RETRIEVAL = "knowledge_base_retrieval"
TOOL_BACKEND_IMAGE_ANALYSIS = "image_analysis"
VALID_TOOL_BACKENDS = {
    TOOL_BACKEND_SANDBOX,
    TOOL_BACKEND_WEB_SEARCH,
    TOOL_BACKEND_INTERNAL_HTTP,
    TOOL_BACKEND_KB_RETRIEVAL,
    TOOL_BACKEND_IMAGE_ANALYSIS,
}


def tool_execution_backend(spec: dict[str, Any]) -> str:
    execution_backend = str(spec.get("execution_backend", "")).strip().lower()
    if execution_backend:
        return execution_backend
    legacy_transport = str(spec.get("transport", "")).strip().lower()
    if legacy_transport == "sandbox_http":
        return TOOL_BACKEND_SANDBOX
    if legacy_transport == "mcp":
        legacy_tool_name = str(spec.get("tool_name", "")).strip().lower()
        return TOOL_BACKEND_WEB_SEARCH if legacy_tool_name in {"", "web_search"} else TOOL_BACKEND_INTERNAL_HTTP
    return ""


def active_runtime_knowledge_base_payload(database_url: str, config: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        platform_runtime = get_active_platform_runtime(database_url, config)
        return list_active_runtime_knowledge_bases(platform_runtime, database_url=database_url), platform_runtime
    except PlatformControlPlaneError as exc:
        return {
            "knowledge_bases": [],
            "default_knowledge_base_id": None,
            "selection_required": False,
            "configuration_message": exc.message,
        }, {}


def active_bound_knowledge_bases(database_url: str, config: Any) -> list[dict[str, Any]]:
    platform_runtime = get_active_platform_runtime(database_url, config)
    payload = list_active_runtime_knowledge_bases(platform_runtime, database_url=database_url)
    return [item for item in payload.get("knowledge_bases", []) if isinstance(item, dict)]


def find_active_bound_knowledge_base(database_url: str, config: Any, *, knowledge_base_id: str) -> dict[str, Any]:
    normalized = str(knowledge_base_id or "").strip()
    if not normalized:
        raise CatalogError("invalid_execution_config", "execution_config.knowledge_base_id is required")
    try:
        for knowledge_base in active_bound_knowledge_bases(database_url, config):
            if str(knowledge_base.get("id") or "").strip() == normalized:
                return knowledge_base
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc
    raise CatalogError(
        "knowledge_base_not_bound",
        "Knowledge base retrieval tools must reference a knowledge base bound to the active deployment vector store.",
        status_code=409,
        details={"knowledge_base_id": normalized},
    )


def knowledge_retrieval_runtime_is_local(platform_runtime: dict[str, Any]) -> bool:
    capabilities = platform_runtime.get("capabilities") if isinstance(platform_runtime.get("capabilities"), dict) else {}
    for capability_key in ["embeddings", "vector_store"]:
        binding = capabilities.get(capability_key) if isinstance(capabilities.get(capability_key), dict) else {}
        if str(binding.get("provider_origin") or "local").strip().lower() == "cloud":
            return False
    return True


def knowledge_base_retrieval_input_schema() -> dict[str, Any]:
    return build_knowledge_base_retrieval_input_schema()


def knowledge_base_retrieval_output_schema() -> dict[str, Any]:
    return build_knowledge_base_retrieval_output_schema()


def _tool_creation_backend_option(execution_backend: str, template: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_backend": execution_backend,
        "requires_knowledge_base": False,
        "template": template,
    }


def _build_sandbox_tool_template() -> dict[str, Any]:
    return {
        "id": "tool.custom_python_exec",
        "visibility": "private",
        "publish": False,
        "name": "Python Execution",
        "description": "Runs constrained Python code in the sandbox runtime.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "input": {},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": ["code"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "result": {},
                "error": {},
            },
            "required": ["stdout", "stderr"],
            "additionalProperties": True,
        },
        "safety_policy": {"timeout_seconds": 5, "network_access": False, "allow_imports": False},
        "offline_compatible": True,
        "execution_backend": TOOL_BACKEND_SANDBOX,
        "execution_config": {},
        "permissions": {},
    }


def _build_web_search_tool_template() -> dict[str, Any]:
    return {
        "id": "tool.custom_web_search",
        "visibility": "private",
        "publish": False,
        "name": "Web Search",
        "description": "Searches the web through the MCP gateway's SearXNG-backed runner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                "language": {"type": "string"},
                "time_range": {"type": "string", "enum": ["day", "month", "year"]},
                "safesearch": {"type": "integer", "enum": [0, 1, 2]},
                "categories": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "results": {"type": "array", "items": {"type": "object"}, "additionalProperties": True},
            },
            "required": ["query", "results"],
            "additionalProperties": True,
        },
        "safety_policy": {"timeout_seconds": 8, "network_access": True},
        "offline_compatible": False,
        "execution_backend": TOOL_BACKEND_WEB_SEARCH,
        "execution_config": {
            "internal_tool_name": "web_search",
            "gateway_internal_path": "/v1/internal/tools/web-search",
        },
        "permissions": {},
    }


def _build_internal_http_tool_template() -> dict[str, Any]:
    return {
        "id": "tool.internal_http",
        "visibility": "private",
        "publish": False,
        "name": "Internal HTTP Tool",
        "description": "Calls a backend-owned internal HTTP integration.",
        "input_schema": {"type": "object", "additionalProperties": True},
        "output_schema": {"type": "object", "additionalProperties": True},
        "safety_policy": {},
        "offline_compatible": True,
        "execution_backend": TOOL_BACKEND_INTERNAL_HTTP,
        "execution_config": {},
        "permissions": {},
    }


def _build_image_analysis_tool_template(tasks: list[str] | None = None) -> dict[str, Any]:
    task_values = tasks or list(IMAGE_ANALYSIS_TASKS)
    return {
        "id": "tool.custom_image_analysis",
        "visibility": "private",
        "publish": False,
        "name": "Image Analysis",
        "description": "Analyzes local image payloads for license plates, objects, and captions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image": {
                    "type": "object",
                    "properties": {
                        "data_base64": {"type": "string"},
                        "mime_type": {"type": "string"},
                    },
                    "required": ["data_base64", "mime_type"],
                    "additionalProperties": False,
                },
                "tasks": {
                    "type": "array",
                    "items": {"type": "string", "enum": task_values},
                    "minItems": 1,
                },
                "options": {"type": "object", "additionalProperties": True},
            },
            "required": ["image", "tasks"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object", "additionalProperties": True},
        "safety_policy": {"timeout_seconds": 30, "network_access": False},
        "offline_compatible": True,
        "execution_backend": TOOL_BACKEND_IMAGE_ANALYSIS,
        "transport": "image_analysis_http",
        "execution_config": {},
        "permissions": {},
    }


def _tool_identifier_part(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    normalized = re.sub(r"[^a-z0-9.-]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip(".-")
    return normalized or "knowledge-base"


def build_knowledge_base_retrieval_tool_template(knowledge_base: dict[str, Any], *, offline_compatible: bool) -> dict[str, Any]:
    knowledge_base_id = str(knowledge_base.get("id") or "").strip()
    slug = str(knowledge_base.get("slug") or knowledge_base_id).strip()
    display_name = str(knowledge_base.get("display_name") or slug or knowledge_base_id).strip()
    return {
        "id": f"tool.kb_retrieval.{_tool_identifier_part(slug or knowledge_base_id)}",
        "visibility": "private",
        "publish": False,
        "name": f"{display_name} Retrieval",
        "description": f"Retrieves relevant passages from {display_name}.",
        "input_schema": knowledge_base_retrieval_input_schema(),
        "output_schema": knowledge_base_retrieval_output_schema(),
        "safety_policy": {"timeout_seconds": 8, "network_access": not offline_compatible},
        "offline_compatible": offline_compatible,
        "execution_backend": TOOL_BACKEND_KB_RETRIEVAL,
        "execution_config": {
            "knowledge_base_id": knowledge_base_id,
            "retrieval_defaults": dict(DEFAULT_RETRIEVAL_OPTIONS),
        },
        "permissions": {},
    }


def build_tool_creation_options(database_url: str, *, config: Any) -> dict[str, Any]:
    runtime_payload, platform_runtime = active_runtime_knowledge_base_payload(database_url, config)
    knowledge_bases = list(runtime_payload.get("knowledge_bases") or [])
    offline_compatible = knowledge_retrieval_runtime_is_local(platform_runtime)
    image_tasks = sorted(image_analysis_available_tasks(database_url, config))
    execution_backends: list[dict[str, Any]] = [
        _tool_creation_backend_option(TOOL_BACKEND_SANDBOX, _build_sandbox_tool_template()),
        _tool_creation_backend_option(TOOL_BACKEND_WEB_SEARCH, _build_web_search_tool_template()),
        _tool_creation_backend_option(TOOL_BACKEND_INTERNAL_HTTP, _build_internal_http_tool_template()),
    ]
    if image_tasks:
        execution_backends.append(_tool_creation_backend_option(TOOL_BACKEND_IMAGE_ANALYSIS, _build_image_analysis_tool_template(image_tasks)))
    if knowledge_bases:
        execution_backends.append(
            {
                "execution_backend": TOOL_BACKEND_KB_RETRIEVAL,
                "requires_knowledge_base": True,
                "knowledge_bases": knowledge_bases,
                "templates_by_knowledge_base_id": {
                    str(knowledge_base.get("id") or ""): build_knowledge_base_retrieval_tool_template(
                        knowledge_base,
                        offline_compatible=offline_compatible,
                    )
                    for knowledge_base in knowledge_bases
                    if str(knowledge_base.get("id") or "").strip()
                },
            }
        )
    return {
        "execution_backends": execution_backends,
        "knowledge_bases": knowledge_bases,
        "default_knowledge_base_id": runtime_payload.get("default_knowledge_base_id"),
        "selection_required": bool(runtime_payload.get("selection_required", False)),
        "configuration_message": runtime_payload.get("configuration_message"),
    }


def image_analysis_available_tasks(database_url: str, config: Any) -> set[str]:
    try:
        adapter = resolve_image_analysis_adapter(database_url, config)
        resources, status_code = adapter.list_resources()
    except Exception:
        return set()
    if status_code < 200 or status_code >= 300:
        return set()
    return available_tasks_from_resources(resources)


def ensure_execution_config(database_url: str, *, config: Any | None, execution_backend: str, execution_config: dict[str, Any]) -> None:
    if execution_backend != TOOL_BACKEND_KB_RETRIEVAL:
        return
    knowledge_base_id = str(execution_config.get("knowledge_base_id") or "").strip()
    if not knowledge_base_id:
        raise CatalogError("invalid_execution_config", "execution_config.knowledge_base_id is required for knowledge_base_retrieval tools")
    retrieval_defaults = execution_config.get("retrieval_defaults", {})
    if retrieval_defaults is not None and not isinstance(retrieval_defaults, dict):
        raise CatalogError("invalid_execution_config", "execution_config.retrieval_defaults must be an object")
    if config is not None:
        find_active_bound_knowledge_base(database_url, config, knowledge_base_id=knowledge_base_id)


def validate_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    execution_backend = runtime_checks["execution_backend"]
    if execution_backend == TOOL_BACKEND_SANDBOX:
        _validate_sandbox_backend(database_url=database_url, config=config, spec=spec, runtime_checks=runtime_checks, errors=errors)
    elif execution_backend == TOOL_BACKEND_WEB_SEARCH:
        _validate_mcp_gateway_backend(database_url=database_url, config=config, runtime_checks=runtime_checks, errors=errors)
    elif execution_backend == TOOL_BACKEND_KB_RETRIEVAL:
        _validate_knowledge_base_retrieval_backend(database_url=database_url, config=config, spec=spec, runtime_checks=runtime_checks, errors=errors)
    elif execution_backend == TOOL_BACKEND_INTERNAL_HTTP:
        runtime_checks["provider_reachable"] = True
    elif execution_backend == TOOL_BACKEND_IMAGE_ANALYSIS:
        _validate_image_analysis_backend(database_url=database_url, config=config, runtime_checks=runtime_checks, errors=errors)
    else:
        errors.append(f"Unsupported execution backend '{execution_backend}'.")


def _validate_sandbox_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    try:
        adapter = resolve_sandbox_execution_adapter(database_url, config)
        health = adapter.health()
        runtime_checks["provider_reachable"] = bool(health.get("reachable", False))
        runtime_checks["provider_status_code"] = health.get("status_code")
        safety_policy = spec.get("safety_policy") if isinstance(spec.get("safety_policy"), dict) else {}
        dry_run_payload, dry_run_status = adapter.execute(
            code=str(safety_policy.get("dry_run_code", "result = {'status': 'ok'}")),
            language="python",
            input_payload={},
            timeout_seconds=int(safety_policy.get("timeout_seconds", 5) or 5),
            policy=safety_policy,
        )
        dry_run_ok = dry_run_payload is not None and 200 <= dry_run_status < 300 and not dry_run_payload.get("error")
        runtime_checks["sandbox_dry_run_ok"] = dry_run_ok
        runtime_checks["sandbox_dry_run_status_code"] = dry_run_status
        if not runtime_checks["provider_reachable"]:
            errors.append("Sandbox runtime provider is not reachable.")
        if not dry_run_ok:
            errors.append("Sandbox dry-run execution failed.")
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code
        runtime_checks["sandbox_dry_run_ok"] = False


def _validate_mcp_gateway_backend(
    *,
    database_url: str,
    config: Any,
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    try:
        adapter = resolve_mcp_runtime_adapter(database_url, config)
        health = adapter.health()
        runtime_checks["provider_reachable"] = bool(health.get("reachable", False))
        runtime_checks["provider_status_code"] = health.get("status_code")
        if hasattr(adapter, "list_tools"):
            tools_payload, tools_status = adapter.list_tools()
            runtime_checks["tools_status_code"] = tools_status
            tools = tools_payload.get("tools") if isinstance(tools_payload, dict) else []
            available_names = {
                str(item.get("tool_name", "")).strip()
                for item in tools
                if isinstance(item, dict) and str(item.get("tool_name", "")).strip()
            }
            runtime_checks["available_tool_names"] = sorted(available_names)
            runtime_checks["tool_discovered"] = "web_search" in available_names if available_names else runtime_checks["provider_reachable"]
        if not runtime_checks["provider_reachable"]:
            errors.append("MCP gateway provider is not reachable.")
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code


def _validate_knowledge_base_retrieval_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    execution_config = spec.get("execution_config") if isinstance(spec.get("execution_config"), dict) else {}
    knowledge_base_id = str(execution_config.get("knowledge_base_id") or "").strip()
    runtime_checks["knowledge_base_id"] = knowledge_base_id or None
    runtime_checks["knowledge_base_bound"] = False
    try:
        if not knowledge_base_id:
            raise CatalogError("invalid_execution_config", "execution_config.knowledge_base_id is required")
        knowledge_base = find_active_bound_knowledge_base(database_url, config, knowledge_base_id=knowledge_base_id)
        runtime_checks["knowledge_base_bound"] = True
        runtime_checks["knowledge_base_display_name"] = knowledge_base.get("display_name")
        runtime_checks["provider_reachable"] = True
    except CatalogError as exc:
        errors.append(exc.message)
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code


def execute_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    execution_backend = tool_execution_backend(spec)
    if execution_backend == TOOL_BACKEND_SANDBOX:
        return _execute_sandbox_backend(database_url=database_url, config=config, spec=spec, tool_input=tool_input)
    if execution_backend == TOOL_BACKEND_WEB_SEARCH:
        return _execute_mcp_gateway_web_search_backend(
            database_url=database_url,
            config=config,
            spec=spec,
            tool_input=tool_input,
            request_metadata=request_metadata,
        )
    if execution_backend == TOOL_BACKEND_KB_RETRIEVAL:
        return _execute_knowledge_base_retrieval_backend(database_url=database_url, config=config, spec=spec, tool_input=tool_input)
    if execution_backend == TOOL_BACKEND_IMAGE_ANALYSIS:
        return _execute_image_analysis_backend(database_url=database_url, config=config, spec=spec, tool_input=tool_input)
    raise CatalogError("invalid_execution_backend", f"Unsupported execution backend '{execution_backend}'.")


def _validate_image_analysis_backend(
    *,
    database_url: str,
    config: Any,
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    try:
        adapter = resolve_image_analysis_adapter(database_url, config)
        health = adapter.health()
        resources, resources_status = adapter.list_resources()
        runtime_checks["provider_reachable"] = bool(health.get("reachable", False))
        runtime_checks["provider_status_code"] = health.get("status_code")
        runtime_checks["resources_status_code"] = resources_status
        runtime_checks["resource_count"] = len(resources)
        if not runtime_checks["provider_reachable"]:
            errors.append("Image analysis runtime provider is not reachable.")
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code


def _execute_sandbox_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    code = str(tool_input.get("code", "")).strip()
    if not code:
        raise CatalogError("invalid_tool_input", "Sandbox tools require input.code")
    safety_policy = spec.get("safety_policy") if isinstance(spec.get("safety_policy"), dict) else {}
    timeout_seconds = int(tool_input.get("timeout_seconds") or safety_policy.get("timeout_seconds") or 5)
    try:
        adapter = resolve_sandbox_execution_adapter(database_url, config)
        return adapter.execute(
            code=code,
            language="python",
            input_payload=tool_input.get("input", {}),
            timeout_seconds=timeout_seconds,
            policy=safety_policy,
        )
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc


def _execute_knowledge_base_retrieval_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    execution_config = spec.get("execution_config") if isinstance(spec.get("execution_config"), dict) else {}
    knowledge_base_id = str(execution_config.get("knowledge_base_id") or "").strip()
    if not knowledge_base_id:
        raise CatalogError("invalid_execution_config", "execution_config.knowledge_base_id is required")
    retrieval_defaults = execution_config.get("retrieval_defaults") if isinstance(execution_config.get("retrieval_defaults"), dict) else {}
    payload = {**retrieval_defaults, **tool_input}
    try:
        find_active_bound_knowledge_base(database_url, config, knowledge_base_id=knowledge_base_id)
        return query_knowledge_base(
            database_url,
            config=config,
            knowledge_base_id=knowledge_base_id,
            payload=payload,
        ), 200
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc


def _execute_mcp_gateway_web_search_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    try:
        adapter = resolve_mcp_runtime_adapter(database_url, config)
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc

    if str(spec.get("transport", "")).strip().lower() == "mcp" and hasattr(adapter, "invoke"):
        return adapter.invoke(
            tool_name=str(spec.get("tool_name") or "web_search").strip() or "web_search",
            arguments=tool_input,
            request_metadata=request_metadata,
        )
    endpoint_url = str(adapter.binding.endpoint_url).rstrip("/")
    path = str((spec.get("execution_config") if isinstance(spec.get("execution_config"), dict) else {}).get("gateway_internal_path", "/v1/internal/tools/web-search"))
    payload, status_code = http_json_request(
        endpoint_url + path,
        method="POST",
        payload={
            "arguments": tool_input,
            "request_metadata": request_metadata,
        },
        headers={"X-Service-Token": str(config.mcp_gateway_service_token)},
    )
    return payload if isinstance(payload, dict) else None, status_code


def _execute_image_analysis_backend(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    image = tool_input.get("image")
    tasks = tool_input.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        execution_config = spec.get("execution_config") if isinstance(spec.get("execution_config"), dict) else {}
        tasks = execution_config.get("tasks")
    if not isinstance(image, dict):
        raise CatalogError("invalid_tool_input", "Image analysis tools require input.image")
    if not isinstance(tasks, list) or not tasks:
        raise CatalogError("invalid_tool_input", "Image analysis tools require input.tasks")
    try:
        adapter = resolve_image_analysis_adapter(database_url, config)
        resource_policy = dict(adapter.binding.resource_policy or {})
        task_defaults = dict(resource_policy.get("task_defaults") or {})
        normalized_tasks = [str(item).strip().lower() for item in tasks if str(item).strip()]
        require_image_analysis_task_defaults(normalized_tasks, task_defaults)
        return adapter.analyze(
            payload={
                "image": image,
                "tasks": normalized_tasks,
                "options": dict(tool_input.get("options") or {}) if isinstance(tool_input.get("options"), dict) else {},
                "runtime": {
                    "resources": [dict(resource) for resource in adapter.binding.resources],
                    "task_defaults": task_defaults,
                },
            }
        )
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc


def mcp_metadata_defaults_for_tool_spec(tool_spec: dict[str, Any]) -> dict[str, Any]:
    execution_backend = tool_execution_backend(tool_spec) or TOOL_BACKEND_INTERNAL_HTTP
    if execution_backend == TOOL_BACKEND_SANDBOX:
        return {
            "category": "code_execution",
            "capabilities": ["python", "code-execution", "calculation", "data-transformation", "sandboxed-execution"],
            "local": True,
            "stateless": True,
            "sandboxed": True,
            "risk_level": "high",
            "data_access": "none",
            "output_freshness": "runtime_generated",
            "audit_level": "elevated",
        }
    if execution_backend == TOOL_BACKEND_WEB_SEARCH:
        return {
            "category": "web_search",
            "capabilities": ["web-search", "fresh-information", "source-discovery", "fact-checking", "public-research"],
            "local": False,
            "stateless": True,
            "sandboxed": False,
            "risk_level": "medium",
            "data_access": "public_web",
            "output_freshness": "fresh",
            "audit_level": "standard",
        }
    if execution_backend == TOOL_BACKEND_KB_RETRIEVAL:
        return {
            "category": "knowledge_retrieval",
            "capabilities": ["knowledge-base", "retrieval", "semantic-search", "source-grounding"],
            "local": bool(tool_spec.get("offline_compatible", False)),
            "stateless": True,
            "sandboxed": False,
            "risk_level": "low",
            "data_access": "workspace",
            "output_freshness": "static",
            "audit_level": "standard",
        }
    if execution_backend == TOOL_BACKEND_IMAGE_ANALYSIS:
        return {
            "category": "data_analysis",
            "capabilities": ["image-analysis", "license-plate-recognition", "object-detection", "image-captioning"],
            "local": True,
            "stateless": True,
            "sandboxed": False,
            "risk_level": "medium",
            "data_access": "user_data",
            "output_freshness": "runtime_generated",
            "audit_level": "standard",
        }
    return {
        "category": "custom",
        "capabilities": [],
        "local": bool(tool_spec.get("offline_compatible", False)),
        "stateless": True,
        "sandboxed": False,
        "risk_level": "medium",
        "data_access": "none",
        "output_freshness": "runtime_generated",
        "audit_level": "standard",
    }
