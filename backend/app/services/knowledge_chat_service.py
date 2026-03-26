from __future__ import annotations

from typing import Any

from flask import g

from ..config import AuthConfig
from .agent_engine_client import AgentEngineClientError, create_execution
from .chat_inference import coerce_chat_messages
from .context_management import list_active_runtime_knowledge_bases, resolve_runtime_knowledge_base_selection
from .knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID, ensure_knowledge_chat_agent
from .modelops_common import ModelOpsError
from .modelops_runtime import ensure_model_invokable
from .platform_service import get_active_platform_runtime
from .platform_types import PlatformControlPlaneError
from .runtime_profile_service import resolve_runtime_profile


def _trim_snippet(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _serialize_source(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    text = str(result.get("text", "")).strip()
    title = str(metadata.get("title", "")).strip() or str(result.get("id", "")).strip()
    uri_raw = metadata.get("uri")
    uri = str(uri_raw).strip() if uri_raw is not None else ""
    source_type_raw = metadata.get("source_type")
    source_type = str(source_type_raw).strip() if source_type_raw is not None else ""
    return {
        "id": str(result.get("id", "")).strip(),
        "title": title,
        "snippet": _trim_snippet(text),
        "uri": uri or None,
        "source_type": source_type or None,
        "metadata": metadata,
        "score": result.get("score"),
        "score_kind": result.get("score_kind"),
    }


def _normalize_sources(execution_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    retrieval_calls = result.get("retrieval_calls") if isinstance(result.get("retrieval_calls"), list) else []
    first_call = retrieval_calls[0] if retrieval_calls and isinstance(retrieval_calls[0], dict) else {}
    rows = first_call.get("results") if isinstance(first_call.get("results"), list) else []
    sources = [_serialize_source(item) for item in rows if isinstance(item, dict)]
    retrieval = {
        "index": str(first_call.get("index", "")).strip(),
        "result_count": int(first_call.get("result_count", len(sources)) or 0),
    }
    return sources, retrieval


def _build_execution_messages(prompt: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        *history,
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


def run_knowledge_chat(
    *,
    database_url: str,
    config: AuthConfig,
    request_id: str,
    prompt: str,
    requested_model_id: str,
    requested_knowledge_base_id: str | None,
    history_payload: Any,
    create_execution_fn=None,
    get_active_platform_runtime_fn=None,
    resolve_runtime_profile_fn=None,
    ensure_knowledge_chat_agent_fn=None,
) -> tuple[dict[str, Any], int]:
    normalized_prompt = str(prompt).strip()
    normalized_model = str(requested_model_id).strip()
    if not normalized_model:
        return {"error": "invalid_model", "message": "model is required"}, 400
    if not normalized_prompt:
        return {"error": "invalid_prompt", "message": "prompt is required"}, 400

    create_execution_impl = create_execution_fn or create_execution
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    resolve_runtime_profile_impl = resolve_runtime_profile_fn or resolve_runtime_profile
    ensure_knowledge_chat_agent_impl = ensure_knowledge_chat_agent_fn or ensure_knowledge_chat_agent
    user_id = int(g.current_user["id"])
    user_role = str(g.current_user.get("role", "user"))

    history = coerce_chat_messages(history_payload)
    try:
        resolved_model = resolve_model_for_inference(
            database_url,
            config=config,
            user_id=user_id,
            user_role=user_role,
            requested_model_id=normalized_model,
        )
    except ModelOpsError as exc:
        return {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code

    ensure_knowledge_chat_agent_impl(database_url)
    try:
        platform_runtime = get_active_platform_runtime_impl(database_url, config)
    except PlatformControlPlaneError as exc:
        return {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code
    try:
        selected_knowledge_base = resolve_runtime_knowledge_base_selection(
            platform_runtime,
            database_url=database_url,
            knowledge_base_id=requested_knowledge_base_id,
        )
    except PlatformControlPlaneError as exc:
        return {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code

    response_payload, execution_status = create_execution_impl(
        base_url=config.agent_engine_url.rstrip("/"),
        service_token=config.agent_engine_service_token,
        request_id=request_id,
        agent_id=KNOWLEDGE_CHAT_AGENT_ID,
        execution_input={
            "prompt": normalized_prompt,
            "model": str(resolved_model.get("id") or normalized_model),
            "messages": _build_execution_messages(normalized_prompt, history),
            "retrieval": {
                "index": str(selected_knowledge_base["index_name"]),
                "top_k": config.product_rag_top_k,
            },
        },
        requested_by_user_id=user_id,
        requested_by_role=user_role,
        runtime_profile=resolve_runtime_profile_impl(database_url),
        platform_runtime=platform_runtime,
    )
    execution_payload = response_payload.get("execution") if isinstance(response_payload.get("execution"), dict) else {}
    result = execution_payload.get("result") if isinstance(execution_payload.get("result"), dict) else {}
    sources, retrieval = _normalize_sources(execution_payload)
    return {
        "output": str(result.get("output_text", "")).strip(),
        "response": execution_payload,
        "sources": sources,
        "retrieval": retrieval,
        "knowledge_base_id": str(selected_knowledge_base["id"]),
    }, 200 if 200 <= execution_status < 300 else execution_status


def list_knowledge_chat_knowledge_bases(
    *,
    database_url: str,
    config: AuthConfig,
    get_active_platform_runtime_fn=None,
) -> tuple[dict[str, Any], int]:
    get_active_platform_runtime_impl = get_active_platform_runtime_fn or get_active_platform_runtime
    try:
        platform_runtime = get_active_platform_runtime_impl(database_url, config)
    except PlatformControlPlaneError as exc:
        return {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code
    return list_active_runtime_knowledge_bases(platform_runtime, database_url=database_url), 200


def map_knowledge_chat_engine_error(exc: AgentEngineClientError) -> tuple[dict[str, Any], int]:
    return {"error": exc.code, "message": exc.message}, exc.status_code
