from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Iterator

from ..config import AuthConfig
from ..services.agent_engine_client import AgentEngineClientError, create_execution, stream_execution
from ..services.context_management import list_active_runtime_knowledge_bases, resolve_runtime_knowledge_base_selection
from ..services.knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID, ensure_knowledge_chat_agent
from ..services.message_content import coerce_llm_messages, content_text, message_content_parts, normalize_content_parts, text_message, text_part
from ..services.modelops_common import ModelOpsError
from ..services.modelops_runtime import ensure_model_invokable
from ..services.platform_service import get_active_platform_runtime
from ..services.platform_types import PlatformControlPlaneError
from ..services.platform_runtime import get_active_platform_runtime_for_dispatch
from ..services.retrieval_result_projection import normalize_execution_retrieval
from ..services.runtime_profile_service import resolve_runtime_profile

DEFAULT_TITLE = "New conversation"
DEFAULT_TITLE_SOURCE = "auto"
MAX_CONTEXT_MESSAGES = 14
CONTEXT_CHAR_BUDGET = 8000
_AGENT_ENGINE_TIMEOUT_BUFFER_SECONDS = 10.0
_PROMPT_CACHE_PREFIX_ROLES = {"system", "developer"}
WORKFLOW_AUTOSTART_PROMPT = "Start the workflow."


class PlaygroundExecutionValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class PlaygroundExecutionRequest:
    playground_kind: str
    session_id: str
    conversation_kind: str
    assistant_ref: str | None
    model_id: str | None
    knowledge_base_id: str | None
    prompt: str
    user_content_parts: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    conversation_title: str | None = None
    title_source: str | None = None
    workflow_state: dict[str, Any] | None = None


@dataclass(slots=True)
class PlaygroundExecutionResult:
    output: str
    response: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    retrieval: dict[str, Any] | None = None
    knowledge_base_id: str | None = None
    statuses: list[dict[str, Any]] = field(default_factory=list)
    workflow_state: dict[str, Any] | None = None
    workflow_status: str | None = None
    content_parts: list[dict[str, Any]] = field(default_factory=list)


def serialize_message(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata_json")
    if not isinstance(metadata, dict):
        metadata = {}
    content_parts = message_content_parts({"content": row.get("content", ""), "metadata": metadata}, allow_image_parts=True)
    return {
        "id": str(row.get("id", "")),
        "role": str(row.get("role", "")),
        "content": content_text(content_parts) or str(row.get("content", "")),
        "content_parts": content_parts,
        "metadata": metadata,
        "createdAt": serialize_datetime(row.get("created_at")),
    }


def serialize_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value is not None else None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _status_now() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def start_status(kind: str, label: str, *, summary: str | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": f"{kind}-{_utc_now().timestamp()}",
        "kind": kind,
        "label": label,
        "state": "running",
        "started_at": _status_now(),
        "completed_at": None,
        "duration_ms": None,
        "summary": summary,
        "details": details or {},
        "_started_monotonic": monotonic(),
    }


def complete_status(status: dict[str, Any], *, label: str | None = None, summary: str | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    started = status.pop("_started_monotonic", None)
    completed = dict(status)
    completed["state"] = "completed"
    completed["completed_at"] = _status_now()
    completed["duration_ms"] = int((monotonic() - started) * 1000) if isinstance(started, (int, float)) else None
    if label is not None:
        completed["label"] = label
    if summary is not None:
        completed["summary"] = summary
    if details is not None:
        completed["details"] = details
    return completed


def public_status(status: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in status.items() if not key.startswith("_")}


def normalize_prompt(value: Any) -> str:
    prompt = str(value or "").strip()
    if not prompt:
        raise PlaygroundExecutionValidationError("invalid_prompt", "prompt is required")
    return prompt


def auto_title_from_prompt(prompt: str) -> str:
    return prompt[:64] or DEFAULT_TITLE


def build_context_messages(messages: list[dict[str, Any]], *, prompt: str) -> list[dict[str, Any]]:
    stable_messages: list[dict[str, Any]] = []
    dynamic_messages: list[dict[str, Any]] = []
    for message in messages:
        content = content_text(message)
        if not content:
            continue
        role = str(message.get("role") or "").strip().lower()
        if role in _PROMPT_CACHE_PREFIX_ROLES:
            stable_messages.append(message)
        else:
            dynamic_messages.append(message)

    reversed_messages = list(reversed(dynamic_messages))
    selected: list[dict[str, Any]] = []
    running_chars = 0

    for message in reversed_messages:
        content = content_text(message)
        if not content:
            continue
        if len(selected) >= MAX_CONTEXT_MESSAGES:
            break
        if running_chars + len(content) > CONTEXT_CHAR_BUDGET and selected:
            break
        selected.append(message)
        running_chars += len(content)

    normalized = [
        {
            "role": str(message.get("role") or ""),
            "content": message_content_parts(message),
        }
        for message in stable_messages
    ]
    normalized.extend([
        {
            "role": str(message.get("role") or ""),
            "content": message_content_parts(message),
        }
        for message in reversed(selected)
    ])
    normalized.append(text_message("user", prompt))
    return normalized


def order_messages_for_prompt_cache(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stable_prefix: list[dict[str, Any]] = []
    dynamic_tail: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "").strip().lower()
        if role in _PROMPT_CACHE_PREFIX_ROLES:
            stable_prefix.append(message)
        else:
            dynamic_tail.append(message)
    return [*stable_prefix, *dynamic_tail]


def coerce_engine_messages(messages: Any) -> list[dict[str, Any]]:
    return coerce_llm_messages(messages, allowed_roles={"system", "developer", "user", "assistant", "tool"})


def build_engine_messages(*, prompt: str, history_payload: Any) -> list[dict[str, Any]]:
    return [
        *order_messages_for_prompt_cache(coerce_engine_messages(history_payload)),
        text_message("user", prompt),
    ]


_CITATION_MARKER_RE = re.compile(r"\[(?:\d+(?:\s*,\s*\d+)*)\]")


def add_missing_reference_citation(output: str, references: list[dict[str, Any]]) -> str:
    normalized = output.strip()
    if not normalized or not references or _CITATION_MARKER_RE.search(normalized):
        return normalized

    citation_numbers = ", ".join(str(index) for index in range(1, min(len(references), 3) + 1))
    return f"{normalized} [{citation_numbers}]"


def assistant_content_parts_from_result(result_payload: dict[str, Any], *, fallback_text: str) -> list[dict[str, Any]]:
    parts = normalize_content_parts(
        result_payload.get("content_parts"),
        fallback_text=fallback_text,
        allow_image_parts=True,
    )
    if parts:
        return parts
    return [text_part(fallback_text)] if fallback_text else []


def resolve_model_for_inference(
    database_url: str,
    *,
    config: AuthConfig,
    user_id: int,
    user_role: str,
    requested_model_id: str,
) -> dict[str, Any]:
    return ensure_model_invokable(
        database_url,
        config=config,
        user_id=user_id,
        user_role=user_role,
        model_id=requested_model_id,
    )


def ensure_model_bound_to_active_runtime(platform_runtime: dict[str, Any], requested_model_id: str) -> None:
    capabilities = platform_runtime.get("capabilities") if isinstance(platform_runtime.get("capabilities"), dict) else {}
    llm_binding = capabilities.get("llm_inference") if isinstance(capabilities.get("llm_inference"), dict) else {}
    resources = llm_binding.get("resources") if isinstance(llm_binding.get("resources"), list) else []
    available_model_ids = [
        str(resource.get("id") or "").strip()
        for resource in resources
        if isinstance(resource, dict) and str(resource.get("id") or "").strip()
    ]
    if not available_model_ids:
        raise PlatformControlPlaneError(
            "resource_required",
            "Active LLM deployment is missing model resources",
            status_code=503,
            details={"provider": llm_binding.get("slug")},
        )
    if requested_model_id in available_model_ids:
        return
    raise PlatformControlPlaneError(
        "selected_model_unavailable",
        "Selected model is not available in the active LLM deployment. Choose a model from the current deployment.",
        status_code=409,
        details={
            "model_id": requested_model_id,
            "provider": llm_binding.get("slug"),
            "available_model_ids": available_model_ids,
            "default_model_id": llm_binding.get("default_resource_id"),
            "deployment_profile": (platform_runtime.get("deployment_profile") or {}).get("slug")
            if isinstance(platform_runtime.get("deployment_profile"), dict)
            else None,
        },
    )


def execute_knowledge_request(
    *,
    database_url: str,
    config: AuthConfig,
    request_id: str,
    request: PlaygroundExecutionRequest,
    actor_user_id: int,
    actor_user_role: str,
    create_execution_fn=None,
    get_active_platform_runtime_fn=None,
    resolve_runtime_profile_fn=None,
    ensure_knowledge_chat_agent_fn=None,
    resolve_model_for_inference_fn=None,
) -> PlaygroundExecutionResult:
    if not request.model_id:
        raise PlaygroundExecutionValidationError("invalid_model", "model is required")

    create_execution_impl = create_execution_fn or create_execution
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    resolve_runtime_profile_impl = resolve_runtime_profile_fn or resolve_runtime_profile
    ensure_knowledge_chat_agent_impl = ensure_knowledge_chat_agent_fn or ensure_knowledge_chat_agent
    resolve_model_for_inference_impl = resolve_model_for_inference_fn or resolve_model_for_inference

    prompt = normalize_prompt(request.prompt)
    resolved_model = resolve_model_for_inference_impl(
        database_url,
        config=config,
        user_id=actor_user_id,
        user_role=actor_user_role,
        requested_model_id=request.model_id,
    )
    ensure_knowledge_chat_agent_impl(database_url)
    platform_runtime = get_active_platform_runtime_for_dispatch(
        database_url,
        config,
        get_active_platform_runtime_fn=get_active_platform_runtime_impl,
    )
    ensure_model_bound_to_active_runtime(platform_runtime, str(resolved_model.get("id") or request.model_id))
    selected_knowledge_base = resolve_runtime_knowledge_base_selection(
        platform_runtime,
        database_url=database_url,
        knowledge_base_id=request.knowledge_base_id,
    )

    response_payload, execution_status = create_execution_impl(
        base_url=config.agent_engine_url.rstrip("/"),
        service_token=config.agent_engine_service_token,
        request_id=request_id,
        agent_id=KNOWLEDGE_CHAT_AGENT_ID,
        execution_input={
            "prompt": prompt,
            "model": str(resolved_model.get("id") or request.model_id),
            "messages": build_engine_messages(prompt=prompt, history_payload=request.history),
            "retrieval": {
                "index": str(selected_knowledge_base["index_name"]),
                "query": prompt,
                "top_k": config.product_rag_top_k,
                "filters": {},
                "search_method": "semantic",
                "query_preprocessing": "none",
            },
        },
        requested_by_user_id=actor_user_id,
        requested_by_role=actor_user_role,
        runtime_profile=resolve_runtime_profile_impl(database_url),
        platform_runtime=platform_runtime,
        timeout_seconds=max(float(config.llm_request_timeout_seconds), 1.0) + _AGENT_ENGINE_TIMEOUT_BUFFER_SECONDS,
    )
    execution_payload = response_payload.get("execution") if isinstance(response_payload.get("execution"), dict) else {}
    result_payload = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    sources, retrieval, references = normalize_execution_retrieval(execution_payload)
    if not 200 <= execution_status < 300:
        raise AgentEngineClientError(
            code="knowledge_chat_failed",
            message="Knowledge chat request failed.",
            status_code=execution_status,
            details=response_payload,
        )
    output = add_missing_reference_citation(str(result_payload.get("output_text", "")).strip(), references)
    return PlaygroundExecutionResult(
        output=output,
        response=execution_payload,
        sources=sources,
        references=references,
        retrieval=retrieval,
        knowledge_base_id=str(selected_knowledge_base["id"]),
        content_parts=[text_part(output)] if output else [],
    )


def execute_agent_chat_request(
    *,
    database_url: str,
    config: AuthConfig,
    request_id: str,
    request: PlaygroundExecutionRequest,
    actor_user_id: int,
    actor_user_role: str,
    create_execution_fn=None,
    get_active_platform_runtime_fn=None,
    resolve_runtime_profile_fn=None,
) -> PlaygroundExecutionResult:
    create_execution_impl = create_execution_fn or create_execution
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    resolve_runtime_profile_impl = resolve_runtime_profile_fn or resolve_runtime_profile

    prompt = normalize_prompt(request.prompt) if str(request.prompt or "").strip() else WORKFLOW_AUTOSTART_PROMPT
    platform_runtime = get_active_platform_runtime_for_dispatch(
        database_url,
        config,
        get_active_platform_runtime_fn=get_active_platform_runtime_impl,
    )
    if request.model_id:
        ensure_model_bound_to_active_runtime(platform_runtime, request.model_id)
    response_payload, execution_status = create_execution_impl(
        base_url=config.agent_engine_url.rstrip("/"),
        service_token=config.agent_engine_service_token,
        request_id=request_id,
        agent_id=str(request.assistant_ref or ""),
        execution_input={
            "prompt": prompt,
            "model": request.model_id,
            "messages": build_engine_messages(prompt=prompt, history_payload=request.history),
            "workflow_state": request.workflow_state,
        },
        requested_by_user_id=actor_user_id,
        requested_by_role=actor_user_role,
        runtime_profile=resolve_runtime_profile_impl(database_url),
        platform_runtime=platform_runtime,
        timeout_seconds=max(float(config.llm_request_timeout_seconds), 1.0) + _AGENT_ENGINE_TIMEOUT_BUFFER_SECONDS,
    )
    execution_payload = response_payload.get("execution") if isinstance(response_payload.get("execution"), dict) else {}
    result_payload = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    if not 200 <= execution_status < 300:
        raise AgentEngineClientError(
            code="agent_chat_failed",
            message="Agent chat request failed.",
            status_code=execution_status,
            details=response_payload,
        )
    return PlaygroundExecutionResult(
        output=str(result_payload.get("output_text", "")).strip(),
        response=execution_payload,
        workflow_state=result_payload.get("workflow_state") if isinstance(result_payload.get("workflow_state"), dict) else None,
        workflow_status=str(result_payload.get("workflow_status") or "").strip() or None,
        content_parts=assistant_content_parts_from_result(
            result_payload,
            fallback_text=str(result_payload.get("output_text", "")).strip(),
        ),
    )


def stream_knowledge_request(
    *,
    database_url: str,
    config: AuthConfig,
    request_id: str,
    request: PlaygroundExecutionRequest,
    actor_user_id: int,
    actor_user_role: str,
    stream_execution_fn=None,
    get_active_platform_runtime_fn=None,
    resolve_runtime_profile_fn=None,
    ensure_knowledge_chat_agent_fn=None,
    resolve_model_for_inference_fn=None,
) -> Iterator[dict[str, Any]]:
    if not request.model_id:
        raise PlaygroundExecutionValidationError("invalid_model", "model is required")

    stream_execution_impl = stream_execution_fn or stream_execution
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    resolve_runtime_profile_impl = resolve_runtime_profile_fn or resolve_runtime_profile
    ensure_knowledge_chat_agent_impl = ensure_knowledge_chat_agent_fn or ensure_knowledge_chat_agent
    resolve_model_for_inference_impl = resolve_model_for_inference_fn or resolve_model_for_inference

    prompt = normalize_prompt(request.prompt)
    resolved_model = resolve_model_for_inference_impl(
        database_url,
        config=config,
        user_id=actor_user_id,
        user_role=actor_user_role,
        requested_model_id=request.model_id,
    )
    ensure_knowledge_chat_agent_impl(database_url)
    platform_runtime = get_active_platform_runtime_for_dispatch(
        database_url,
        config,
        get_active_platform_runtime_fn=get_active_platform_runtime_impl,
    )
    ensure_model_bound_to_active_runtime(platform_runtime, str(resolved_model.get("id") or request.model_id))
    selected_knowledge_base = resolve_runtime_knowledge_base_selection(
        platform_runtime,
        database_url=database_url,
        knowledge_base_id=request.knowledge_base_id,
    )
    statuses: list[dict[str, Any]] = []
    output_parts: list[str] = []
    for event in stream_execution_impl(
        base_url=config.agent_engine_url.rstrip("/"),
        service_token=config.agent_engine_service_token,
        request_id=request_id,
        agent_id=KNOWLEDGE_CHAT_AGENT_ID,
        execution_input={
            "prompt": prompt,
            "model": str(resolved_model.get("id") or request.model_id),
            "messages": build_engine_messages(prompt=prompt, history_payload=request.history),
            "retrieval": {
                "index": str(selected_knowledge_base["index_name"]),
                "query": prompt,
                "top_k": config.product_rag_top_k,
                "filters": {},
                "search_method": "semantic",
                "query_preprocessing": "none",
            },
        },
        requested_by_user_id=actor_user_id,
        requested_by_role=actor_user_role,
        runtime_profile=resolve_runtime_profile_impl(database_url),
        platform_runtime=platform_runtime,
        timeout_seconds=max(float(config.llm_request_timeout_seconds), 1.0) + _AGENT_ENGINE_TIMEOUT_BUFFER_SECONDS,
    ):
        event_name = str(event.get("event") or "").strip()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_name == "status":
            statuses.append(data)
            yield {"event": "status", "data": data}
            continue
        if event_name == "delta":
            text = str(data.get("text") or "")
            if text:
                output_parts.append(text)
                yield {"event": "delta", "data": {"text": text}}
            continue
        if event_name == "error":
            raise AgentEngineClientError(
                code=str(data.get("error") or "knowledge_chat_failed"),
                message=str(data.get("message") or "Knowledge chat request failed."),
                status_code=int(data.get("status_code", 502) or 502),
                details=data,
            )
        if event_name != "complete":
            continue

        execution_payload = data.get("execution") if isinstance(data.get("execution"), dict) else {}
        result_payload = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
        sources, retrieval, references = normalize_execution_retrieval(execution_payload)
        output = str(result_payload.get("output_text", "")).strip() or "".join(output_parts).strip()
        output = add_missing_reference_citation(output, references)
        yield {
            "event": "complete",
            "data": PlaygroundExecutionResult(
                output=output,
                response=execution_payload,
                sources=sources,
                references=references,
                retrieval=retrieval,
                knowledge_base_id=str(selected_knowledge_base["id"]),
                statuses=statuses,
                content_parts=[text_part(output)] if output else [],
            ),
        }
        return

    raise AgentEngineClientError(
        code="agent_engine_stream_incomplete",
        message="Agent engine stream ended before completion",
        status_code=502,
    )


def stream_agent_chat_request(
    *,
    database_url: str,
    config: AuthConfig,
    request_id: str,
    request: PlaygroundExecutionRequest,
    actor_user_id: int,
    actor_user_role: str,
    stream_execution_fn=None,
    get_active_platform_runtime_fn=None,
    resolve_runtime_profile_fn=None,
) -> Iterator[dict[str, Any]]:
    stream_execution_impl = stream_execution_fn or stream_execution
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    resolve_runtime_profile_impl = resolve_runtime_profile_fn or resolve_runtime_profile

    prompt = normalize_prompt(request.prompt) if str(request.prompt or "").strip() else WORKFLOW_AUTOSTART_PROMPT
    platform_runtime = get_active_platform_runtime_for_dispatch(
        database_url,
        config,
        get_active_platform_runtime_fn=get_active_platform_runtime_impl,
    )
    if request.model_id:
        ensure_model_bound_to_active_runtime(platform_runtime, request.model_id)
    statuses: list[dict[str, Any]] = []
    output_parts: list[str] = []
    for event in stream_execution_impl(
        base_url=config.agent_engine_url.rstrip("/"),
        service_token=config.agent_engine_service_token,
        request_id=request_id,
        agent_id=str(request.assistant_ref or ""),
        execution_input={
            "prompt": prompt,
            "model": request.model_id,
            "messages": build_engine_messages(prompt=prompt, history_payload=request.history),
            "workflow_state": request.workflow_state,
        },
        requested_by_user_id=actor_user_id,
        requested_by_role=actor_user_role,
        runtime_profile=resolve_runtime_profile_impl(database_url),
        platform_runtime=platform_runtime,
        timeout_seconds=max(float(config.llm_request_timeout_seconds), 1.0) + _AGENT_ENGINE_TIMEOUT_BUFFER_SECONDS,
    ):
        event_name = str(event.get("event") or "").strip()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_name == "status":
            statuses.append(data)
            yield {"event": "status", "data": data}
            continue
        if event_name == "delta":
            text = str(data.get("text") or "")
            if text:
                output_parts.append(text)
                yield {"event": "delta", "data": {"text": text}}
            continue
        if event_name == "error":
            raise AgentEngineClientError(
                code=str(data.get("error") or "agent_chat_failed"),
                message=str(data.get("message") or "Agent chat request failed."),
                status_code=int(data.get("status_code", 502) or 502),
                details=data,
            )
        if event_name != "complete":
            continue

        execution_payload = data.get("execution") if isinstance(data.get("execution"), dict) else {}
        result_payload = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
        output = str(result_payload.get("output_text", "")).strip() or "".join(output_parts).strip()
        yield {
            "event": "complete",
            "data": PlaygroundExecutionResult(
                output=output,
                response=execution_payload,
                statuses=statuses,
                workflow_state=result_payload.get("workflow_state") if isinstance(result_payload.get("workflow_state"), dict) else None,
                workflow_status=str(result_payload.get("workflow_status") or "").strip() or None,
                content_parts=assistant_content_parts_from_result(result_payload, fallback_text=output),
            ),
        }
        return

    raise AgentEngineClientError(
        code="agent_engine_stream_incomplete",
        message="Agent engine stream ended before completion",
        status_code=502,
    )


def list_runtime_knowledge_base_options(
    *,
    database_url: str,
    config: AuthConfig,
    get_active_platform_runtime_fn=None,
) -> tuple[dict[str, Any], int]:
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    platform_runtime = get_active_platform_runtime_impl(database_url, config)
    return list_active_runtime_knowledge_bases(platform_runtime, database_url=database_url), 200
