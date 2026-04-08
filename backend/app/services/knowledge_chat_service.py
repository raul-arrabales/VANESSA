from __future__ import annotations

from typing import Any

from flask import g

from ..application.playground_execution import (
    PlaygroundExecutionRequest,
    PlaygroundExecutionValidationError,
    execute_knowledge_request,
    list_runtime_knowledge_base_options,
)
from ..config import AuthConfig
from .agent_engine_client import AgentEngineClientError, create_execution
from .knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID, ensure_knowledge_chat_agent
from .modelops_common import ModelOpsError
from .modelops_runtime import ensure_model_invokable
from .platform_service import get_active_platform_runtime
from .platform_types import PlatformControlPlaneError
from .runtime_profile_service import resolve_runtime_profile


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
    actor_user_id: int | None = None,
    actor_user_role: str | None = None,
) -> tuple[dict[str, Any], int]:
    user_id = int(actor_user_id) if actor_user_id is not None else int(g.current_user["id"])
    user_role = str(actor_user_role or g.current_user.get("role", "user"))
    try:
        result = execute_knowledge_request(
            database_url=database_url,
            config=config,
            request_id=request_id,
            request=PlaygroundExecutionRequest(
                playground_kind="knowledge",
                session_id="knowledge-chat",
                conversation_kind="knowledge",
                assistant_ref=KNOWLEDGE_CHAT_AGENT_ID,
                model_id=str(requested_model_id or "").strip() or None,
                knowledge_base_id=str(requested_knowledge_base_id or "").strip() or None,
                prompt=str(prompt or ""),
                history=[
                    {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
                    for item in history_payload
                    if isinstance(item, dict)
                ],
            ),
            actor_user_id=user_id,
            actor_user_role=user_role,
            create_execution_fn=create_execution_fn or create_execution,
            get_active_platform_runtime_fn=get_active_platform_runtime_fn or get_active_platform_runtime,
            resolve_runtime_profile_fn=resolve_runtime_profile_fn or resolve_runtime_profile,
            ensure_knowledge_chat_agent_fn=ensure_knowledge_chat_agent_fn or ensure_knowledge_chat_agent,
            resolve_model_for_inference_fn=resolve_model_for_inference,
        )
    except PlaygroundExecutionValidationError as exc:
        return {"error": exc.code, "message": exc.message}, 400
    except ModelOpsError as exc:
        return {"error": exc.code, "message": exc.message, "details": exc.details or None}, exc.status_code
    except PlatformControlPlaneError as exc:
        return {"error": exc.code, "message": exc.message, "details": exc.details or None}, exc.status_code
    except AgentEngineClientError as exc:
        return map_knowledge_chat_engine_error(exc)

    return {
        "output": result.output,
        "response": result.response,
        "sources": result.sources,
        "retrieval": result.retrieval,
        "knowledge_base_id": result.knowledge_base_id,
    }, 200


def list_knowledge_chat_knowledge_bases(
    *,
    database_url: str,
    config: AuthConfig,
    get_active_platform_runtime_fn=None,
) -> tuple[dict[str, Any], int]:
    try:
        return list_runtime_knowledge_base_options(
            database_url=database_url,
            config=config,
            get_active_platform_runtime_fn=get_active_platform_runtime_fn or get_active_platform_runtime,
        )
    except PlatformControlPlaneError as exc:
        return {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code


def map_knowledge_chat_engine_error(exc: AgentEngineClientError) -> tuple[dict[str, Any], int]:
    return {"error": exc.code, "message": exc.message}, exc.status_code
