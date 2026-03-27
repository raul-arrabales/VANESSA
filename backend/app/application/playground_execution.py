from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..config import AuthConfig
from ..services.agent_engine_client import AgentEngineClientError, create_execution
from ..services.context_management import list_active_runtime_knowledge_bases, resolve_runtime_knowledge_base_selection
from ..services.knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID, ensure_knowledge_chat_agent
from ..services.modelops_common import ModelOpsError
from ..services.modelops_runtime import ensure_model_invokable
from ..services.platform_service import get_active_platform_runtime
from ..services.platform_types import PlatformControlPlaneError
from ..services.runtime_profile_service import resolve_runtime_profile

DEFAULT_TITLE = "New conversation"
DEFAULT_TITLE_SOURCE = "auto"
MAX_CONTEXT_MESSAGES = 14
CONTEXT_CHAR_BUDGET = 8000


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
    history: list[dict[str, Any]] = field(default_factory=list)
    conversation_title: str | None = None
    title_source: str | None = None


@dataclass(slots=True)
class PlaygroundExecutionResult:
    output: str
    response: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    retrieval: dict[str, Any] | None = None
    knowledge_base_id: str | None = None


def serialize_message(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata_json")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "id": str(row.get("id", "")),
        "role": str(row.get("role", "")),
        "content": str(row.get("content", "")),
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


def normalize_prompt(value: Any) -> str:
    prompt = str(value or "").strip()
    if not prompt:
        raise PlaygroundExecutionValidationError("invalid_prompt", "prompt is required")
    return prompt


def auto_title_from_prompt(prompt: str) -> str:
    return prompt[:64] or DEFAULT_TITLE


def build_context_messages(messages: list[dict[str, Any]], *, prompt: str) -> list[dict[str, Any]]:
    reversed_messages = list(reversed(messages))
    selected: list[dict[str, Any]] = []
    running_chars = 0

    for message in reversed_messages:
        content = str(message.get("content") or "")
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
            "content": [{"type": "text", "text": str(message.get("content") or "")}],
        }
        for message in reversed(selected)
    ]
    normalized.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
    return normalized


def coerce_engine_messages(messages: Any) -> list[dict[str, Any]]:
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        if not content:
            continue
        normalized.append(
            {
                "role": role,
                "content": [{"type": "text", "text": content}],
            }
        )
    return normalized


def build_engine_messages(*, prompt: str, history_payload: Any) -> list[dict[str, Any]]:
    return [
        *coerce_engine_messages(history_payload),
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
    ]


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
    platform_runtime = get_active_platform_runtime_impl(database_url, config)
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
                "top_k": config.product_rag_top_k,
            },
        },
        requested_by_user_id=actor_user_id,
        requested_by_role=actor_user_role,
        runtime_profile=resolve_runtime_profile_impl(database_url),
        platform_runtime=platform_runtime,
    )
    execution_payload = response_payload.get("execution") if isinstance(response_payload.get("execution"), dict) else {}
    result_payload = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    sources, retrieval = normalize_execution_sources(execution_payload)
    if not 200 <= execution_status < 300:
        raise AgentEngineClientError(
            code="knowledge_chat_failed",
            message="Knowledge chat request failed.",
            status_code=execution_status,
            details=response_payload,
        )
    return PlaygroundExecutionResult(
        output=str(result_payload.get("output_text", "")).strip(),
        response=execution_payload,
        sources=sources,
        retrieval=retrieval,
        knowledge_base_id=str(selected_knowledge_base["id"]),
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


def normalize_execution_sources(execution_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    retrieval_calls = result.get("retrieval_calls") if isinstance(result.get("retrieval_calls"), list) else []
    first_call = retrieval_calls[0] if retrieval_calls and isinstance(retrieval_calls[0], dict) else {}
    rows = first_call.get("results") if isinstance(first_call.get("results"), list) else []
    sources = [serialize_source(item) for item in rows if isinstance(item, dict)]
    retrieval = {
        "index": str(first_call.get("index", "")).strip(),
        "result_count": int(first_call.get("result_count", len(sources)) or 0),
    }
    return sources, retrieval


def serialize_source(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    text = str(result.get("text", "")).strip()
    title = str(metadata.get("title", "")).strip() or str(result.get("id", "")).strip()
    uri_raw = metadata.get("uri")
    source_type_raw = metadata.get("source_type")
    return {
        "id": str(result.get("id", "")).strip(),
        "title": title,
        "snippet": trim_snippet(text),
        "uri": string_or_none(uri_raw),
        "source_type": string_or_none(source_type_raw),
        "metadata": metadata,
        "score": result.get("score"),
        "score_kind": result.get("score_kind"),
    }


def trim_snippet(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
