from __future__ import annotations

from typing import Any

from .catalog_tool_backends import (
    TOOL_BACKEND_IMAGE_ANALYSIS,
    TOOL_BACKEND_IMAGE_GENERATION,
    TOOL_BACKEND_INTERNAL_HTTP,
    TOOL_BACKEND_KB_RETRIEVAL,
    TOOL_BACKEND_SANDBOX,
    TOOL_BACKEND_WEB_SEARCH,
    tool_execution_backend,
)


def catalog_runtime_log_entry(
    stage: str,
    message: str,
    *,
    level: str = "info",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "stage": stage,
        "level": level,
        "message": message,
    }
    if details:
        entry["details"] = details
    return entry


def tool_runtime_input_summary(tool: dict[str, Any], input_payload: dict[str, Any]) -> dict[str, Any]:
    spec = tool.get("spec") if isinstance(tool.get("spec"), dict) else {}
    backend = tool_execution_backend(spec) or TOOL_BACKEND_INTERNAL_HTTP
    summary: dict[str, Any] = {"backend": backend}
    if backend == TOOL_BACKEND_IMAGE_ANALYSIS:
        tasks = input_payload.get("tasks")
        if isinstance(tasks, list):
            summary["tasks"] = [str(task).strip().lower() for task in tasks if str(task).strip()]
        summary["has_image"] = isinstance(input_payload.get("image"), dict)
    elif backend == TOOL_BACKEND_IMAGE_GENERATION:
        tasks = input_payload.get("tasks")
        if isinstance(tasks, list):
            summary["tasks"] = [str(task).strip().lower() for task in tasks if str(task).strip()]
        prompt = str(input_payload.get("prompt") or "").strip()
        if prompt:
            summary["prompt_length"] = len(prompt)
    elif backend == TOOL_BACKEND_SANDBOX:
        code = str(input_payload.get("code") or "")
        if code:
            summary["code_length"] = len(code)
        summary["has_input_payload"] = isinstance(input_payload.get("input"), dict)
    elif backend == TOOL_BACKEND_WEB_SEARCH:
        query = str(input_payload.get("query") or "").strip()
        if query:
            summary["query_length"] = len(query)
        if "top_k" in input_payload:
            summary["top_k"] = input_payload.get("top_k")
    elif backend == TOOL_BACKEND_KB_RETRIEVAL:
        query_text = str(input_payload.get("query_text") or "").strip()
        if query_text:
            summary["query_length"] = len(query_text)
        if "top_k" in input_payload:
            summary["top_k"] = input_payload.get("top_k")
    return summary


def result_warning_summary(result_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(result_payload, dict):
        return None
    warnings = result_payload.get("warnings")
    if not isinstance(warnings, list):
        return None
    warning_codes = [
        str(item.get("code")).strip()
        for item in warnings
        if isinstance(item, dict) and str(item.get("code")).strip()
    ]
    return {
        "warning_count": len(warnings),
        "warning_codes": warning_codes,
    }


def build_catalog_tool_runtime_log(
    *,
    tool: dict[str, Any],
    input_payload: dict[str, Any],
    request_metadata: dict[str, Any],
    result_payload: dict[str, Any] | None,
    status_code: int,
    duration_ms: int,
) -> list[dict[str, Any]]:
    spec = tool.get("spec") if isinstance(tool.get("spec"), dict) else {}
    backend = tool_execution_backend(spec) or TOOL_BACKEND_INTERNAL_HTTP
    summary = tool_runtime_input_summary(tool, input_payload)
    actor_user_id = request_metadata.get("actor_user_id")
    logs = [
        catalog_runtime_log_entry(
            "request_received",
            "Backend accepted the catalog tool test request.",
            details={"tool_id": tool.get("id"), "backend": backend, "actor_user_id": actor_user_id},
        ),
        catalog_runtime_log_entry(
            "input_validated",
            "Backend validated the tool input against the configured schema.",
            details=summary,
        ),
        catalog_runtime_log_entry(
            "runtime_dispatched",
            "Backend dispatched the request to the active runtime adapter.",
            details={"backend": backend},
        ),
    ]
    warning_summary = result_warning_summary(result_payload)
    if warning_summary:
        logs.append(
            catalog_runtime_log_entry(
                "runtime_warnings",
                "Runtime returned warnings while completing the tool test.",
                level="warning",
                details=warning_summary,
            )
        )
    ok = result_payload is not None and 200 <= status_code < 300 and not result_payload.get("error")
    completion_details = {"status_code": status_code, "duration_ms": duration_ms}
    if isinstance(result_payload, dict) and result_payload.get("error"):
        completion_details["error"] = result_payload.get("error")
    logs.append(
        catalog_runtime_log_entry(
            "completed" if ok else "failed",
            "Tool test finished successfully." if ok else "Tool test finished with an error response.",
            level="info" if ok else "error",
            details=completion_details,
        )
    )
    return logs
