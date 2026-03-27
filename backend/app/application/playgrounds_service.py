from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from ..config import AuthConfig
from ..domain.playgrounds import (
    CHAT_PLAYGROUND_KIND,
    KNOWLEDGE_PLAYGROUND_KIND,
    PLAYGROUND_ASSISTANTS,
    conversation_kind_for_playground_kind,
    default_assistant_ref_for_kind,
    playground_kind_for_conversation_kind,
)
from ..infrastructure import playgrounds_repository
from ..services.agent_engine_client import AgentEngineClientError
from ..services.chat_inference import (
    chat_completion_stream_with_allowed_model,
    chat_completion_with_allowed_model,
    extract_output_text,
)
from ..services.modelops_common import ModelOpsError
from ..services.modelops_queries import list_models
from ..services.platform_types import PlatformControlPlaneError
from .playground_execution import (
    PlaygroundExecutionRequest,
    PlaygroundExecutionResult,
    PlaygroundExecutionValidationError,
    auto_title_from_prompt,
    build_context_messages,
    execute_knowledge_request,
    list_runtime_knowledge_base_options,
    normalize_prompt,
    serialize_message,
    serialize_datetime,
    string_or_none,
)

DEFAULT_TITLE_SOURCE = "auto"
DEFAULT_CHAT_TITLE = "New chat session"
DEFAULT_KNOWLEDGE_TITLE = "New knowledge session"
SESSION_UNSET = object()

PlaygroundSessionValidationError = PlaygroundExecutionValidationError
list_knowledge_chat_knowledge_bases = list_runtime_knowledge_base_options


class PlaygroundSessionNotFoundError(Exception):
    pass


class PlaygroundChatExecutionError(RuntimeError):
    def __init__(self, payload: dict[str, Any], status_code: int):
        super().__init__(str(payload.get("message") or payload.get("error") or "playground_chat_failed"))
        self.payload = payload
        self.status_code = status_code


def list_playground_sessions(
    database_url: str,
    *,
    owner_user_id: int,
    playground_kind: str | None = None,
) -> list[dict[str, Any]]:
    if playground_kind:
        conversation_kind = conversation_kind_for_playground_kind(playground_kind)
        rows = playgrounds_repository.list_sessions(
            database_url,
            owner_user_id=owner_user_id,
            conversation_kind=conversation_kind,
        )
        return [_serialize_session_summary(row) for row in rows]

    items: list[dict[str, Any]] = []
    for conversation_kind in ("plain", "knowledge"):
        rows = playgrounds_repository.list_sessions(
            database_url,
            owner_user_id=owner_user_id,
            conversation_kind=conversation_kind,
        )
        items.extend(_serialize_session_summary(row) for row in rows)
    items.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return items


def create_playground_session(
    database_url: str,
    *,
    owner_user_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    playground_kind = _normalize_playground_kind(payload.get("playground_kind"))
    conversation_kind = conversation_kind_for_playground_kind(playground_kind)
    row = playgrounds_repository.create_session(
        database_url,
        owner_user_id=owner_user_id,
        title=_default_title_for_kind(playground_kind),
        title_source=DEFAULT_TITLE_SOURCE,
        assistant_ref=_normalize_assistant_ref(payload.get("assistant_ref"), playground_kind=playground_kind),
        model_id=_normalize_model_id(payload.get("model_selection", payload.get("model_id"))),
        knowledge_base_id=_normalize_knowledge_base_id(payload.get("knowledge_binding", payload.get("knowledge_base_id"))),
        conversation_kind=conversation_kind,
    )
    return _serialize_session_detail(row, [])


def get_playground_session_detail(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
    playground_kind: str | None = None,
) -> dict[str, Any]:
    row, messages = _load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=playground_kind,
    )
    return _serialize_session_detail(row, messages)


def update_playground_session(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))
    updated = playgrounds_repository.update_session(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=session_id,
        title=_normalize_title(payload["title"]) if "title" in payload else SESSION_UNSET,
        title_source="manual" if "title" in payload else SESSION_UNSET,
        assistant_ref=_normalize_assistant_ref(payload.get("assistant_ref"), playground_kind=playground_kind) if "assistant_ref" in payload else SESSION_UNSET,
        model_id=_normalize_model_id(payload.get("model_selection", payload.get("model_id"))) if "model_selection" in payload or "model_id" in payload else SESSION_UNSET,
        knowledge_base_id=_normalize_knowledge_base_id(payload.get("knowledge_binding", payload.get("knowledge_base_id"))) if "knowledge_binding" in payload or "knowledge_base_id" in payload else SESSION_UNSET,
        conversation_kind=str(row.get("conversation_kind", "")),
    )
    if updated is None:
        raise PlaygroundSessionNotFoundError
    return _serialize_session_summary(updated)


def delete_playground_session(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
) -> None:
    row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    deleted = playgrounds_repository.delete_session(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=session_id,
        conversation_kind=str(row.get("conversation_kind", "")),
    )
    if not deleted:
        raise PlaygroundSessionNotFoundError


def send_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    session_id: str,
    prompt: Any,
) -> dict[str, Any]:
    row, history_messages = _load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=None,
    )
    request = _build_execution_request(row=row, history_messages=history_messages, prompt=prompt)
    result = _execute_request(
        database_url,
        config=config,
        request_id=request_id,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        request=request,
    )
    persisted = _persist_execution_result(
        database_url,
        owner_user_id=owner_user_id,
        request=request,
        result=result,
    )
    session = get_playground_session_detail(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=request.playground_kind,
    )
    return _serialize_execution_response(
        session=session,
        persisted=persisted,
        result=result,
    )


def stream_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    session_id: str,
    prompt: Any,
) -> Iterator[dict[str, Any]]:
    row, history_messages = _load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=None,
    )
    request = _build_execution_request(row=row, history_messages=history_messages, prompt=prompt)
    if request.playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        payload = send_playground_message(
            database_url,
            config=config,
            request_id=request_id,
            owner_user_id=owner_user_id,
            owner_role=owner_role,
            session_id=session_id,
            prompt=prompt,
        )
        return iter([{"event": "complete", "data": payload}])
    return _stream_chat_request(
        database_url,
        owner_user_id=owner_user_id,
        request=request,
    )


def get_playground_options(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    models = list_models(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        require_active=True,
        capability_key="llm_inference",
    )
    try:
        knowledge_payload, _status_code = list_knowledge_chat_knowledge_bases(
            database_url=database_url,
            config=config,
        )
    except PlatformControlPlaneError as exc:
        knowledge_payload = {
            "knowledge_bases": [],
            "default_knowledge_base_id": None,
            "selection_required": False,
            "configuration_message": exc.message,
        }
    return {
        "assistants": PLAYGROUND_ASSISTANTS,
        "models": [
            {
                "id": str(item.get("id", "")),
                "display_name": str(item.get("name", "") or item.get("id", "")),
                "task_key": str(item.get("task_key", "")),
            }
            for item in models
        ],
        "knowledge_bases": knowledge_payload.get("knowledge_bases", []),
        "default_knowledge_base_id": knowledge_payload.get("default_knowledge_base_id"),
        "selection_required": bool(knowledge_payload.get("selection_required", False)),
        "configuration_message": knowledge_payload.get("configuration_message"),
    }


def _build_execution_request(
    *,
    row: dict[str, Any],
    history_messages: list[dict[str, Any]],
    prompt: Any,
) -> PlaygroundExecutionRequest:
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))
    prompt_text = normalize_prompt(prompt)
    conversation_title = None
    title_source = None
    if not history_messages and str(row.get("title_source") or DEFAULT_TITLE_SOURCE) == DEFAULT_TITLE_SOURCE:
        conversation_title = auto_title_from_prompt(prompt_text)
        title_source = DEFAULT_TITLE_SOURCE
    return PlaygroundExecutionRequest(
        playground_kind=playground_kind,
        session_id=str(row.get("id", "")),
        conversation_kind=str(row.get("conversation_kind", "")),
        assistant_ref=string_or_none(row.get("assistant_ref")),
        model_id=string_or_none(row.get("model_id")),
        knowledge_base_id=string_or_none(row.get("knowledge_base_id")),
        prompt=prompt_text,
        history=[{"role": str(item.get("role", "")), "content": str(item.get("content", ""))} for item in history_messages],
        conversation_title=conversation_title,
        title_source=title_source,
    )


def _execute_request(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    request: PlaygroundExecutionRequest,
) -> PlaygroundExecutionResult:
    if request.playground_kind == CHAT_PLAYGROUND_KIND:
        return _execute_chat_request(request)
    if not request.knowledge_base_id:
        raise PlaygroundSessionValidationError(
            "knowledge_base_required",
            "knowledge_binding.knowledge_base_id is required for knowledge playground sessions",
        )
    try:
        return execute_knowledge_request(
            database_url=database_url,
            config=config,
            request_id=request_id,
            request=request,
            actor_user_id=owner_user_id,
            actor_user_role=owner_role,
        )
    except (ModelOpsError, PlatformControlPlaneError) as exc:
        raise PlaygroundSessionValidationError(exc.code, exc.message) from exc


def _execute_chat_request(request: PlaygroundExecutionRequest) -> PlaygroundExecutionResult:
    if not request.model_id:
        raise PlaygroundSessionValidationError("invalid_model_id", "model_selection.model_id is required before sending messages")

    llm_response, status_code = chat_completion_with_allowed_model(
        requested_model_id=request.model_id,
        org_id=None,
        group_id=None,
        messages=build_context_messages(request.history, prompt=request.prompt),
        max_tokens=None,
        temperature=None,
    )
    if llm_response is None:
        raise PlaygroundChatExecutionError(
            {"error": "llm_unreachable", "message": "LLM service unavailable"},
            502,
        )
    if status_code >= 400:
        raise PlaygroundChatExecutionError(
            llm_response if isinstance(llm_response, dict) else {"error": "playground_chat_failed"},
            status_code,
        )

    output = extract_output_text(llm_response)
    if not output:
        raise PlaygroundChatExecutionError(
            {"error": "empty_response", "message": "LLM stream completed without assistant output"},
            502,
        )
    return PlaygroundExecutionResult(
        output=output,
        response=llm_response,
    )


def _persist_execution_result(
    database_url: str,
    *,
    owner_user_id: int,
    request: PlaygroundExecutionRequest,
    result: PlaygroundExecutionResult,
) -> dict[str, Any]:
    assistant_metadata = None
    if request.playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        assistant_metadata = {
            "response": result.response,
            "sources": result.sources,
            "retrieval": result.retrieval,
            "knowledge_base_id": result.knowledge_base_id,
        }
    persisted = playgrounds_repository.append_message_pair(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=request.session_id,
        user_content=request.prompt,
        assistant_content=result.output,
        assistant_metadata=assistant_metadata,
        conversation_title=request.conversation_title,
        title_source=request.title_source,
        conversation_kind=request.conversation_kind,
    )
    if persisted is None:
        raise PlaygroundSessionNotFoundError
    return persisted


def _stream_chat_request(
    database_url: str,
    *,
    owner_user_id: int,
    request: PlaygroundExecutionRequest,
) -> Iterator[dict[str, Any]]:
    if not request.model_id:
        raise PlaygroundSessionValidationError("invalid_model_id", "model_selection.model_id is required before sending messages")

    stream, error_payload, status_code = chat_completion_stream_with_allowed_model(
        requested_model_id=request.model_id,
        org_id=None,
        group_id=None,
        messages=build_context_messages(request.history, prompt=request.prompt),
        max_tokens=None,
        temperature=None,
    )
    if error_payload is not None or stream is None:
        raise PlaygroundChatExecutionError(
            error_payload if isinstance(error_payload, dict) else {"error": "llm_unreachable"},
            status_code,
        )

    def _stream() -> Iterator[dict[str, Any]]:
        assistant_output_parts: list[str] = []
        for event in stream:
            event_type = str(event.get("type", "")).strip().lower()
            if event_type == "delta":
                text = str(event.get("text", ""))
                if not text:
                    continue
                assistant_output_parts.append(text)
                yield {"event": "delta", "data": {"text": text}}
                continue

            if event_type == "error":
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    payload = {
                        "error": "playground_chat_failed",
                        "message": "LLM stream failed",
                    }
                yield {
                    "event": "error",
                    "data": {
                        "error": str(payload.get("error") or "playground_chat_failed"),
                        "message": str(payload.get("message") or "LLM stream failed"),
                    },
                }
                return

            if event_type != "complete":
                continue

            llm_response = event.get("response")
            if not isinstance(llm_response, dict):
                llm_response = {"output": [{"content": [{"type": "text", "text": "".join(assistant_output_parts)}]}]}
            output = extract_output_text(llm_response) or "".join(assistant_output_parts)
            if not output:
                yield {
                    "event": "error",
                    "data": {
                        "error": "empty_response",
                        "message": "LLM stream completed without assistant output",
                    },
                }
                return

            persisted = _persist_execution_result(
                database_url,
                owner_user_id=owner_user_id,
                request=request,
                result=PlaygroundExecutionResult(output=output, response=llm_response),
            )
            session = get_playground_session_detail(
                database_url,
                owner_user_id=owner_user_id,
                session_id=request.session_id,
                playground_kind=request.playground_kind,
            )
            yield {
                "event": "complete",
                "data": _serialize_execution_response(
                    session=session,
                    persisted=persisted,
                    result=PlaygroundExecutionResult(output=output, response=llm_response),
                ),
            }
            return

        yield {
            "event": "error",
            "data": {
                "error": "stream_incomplete",
                "message": "LLM stream ended before completion",
            },
        }

    return _stream()


def _serialize_execution_response(
    *,
    session: dict[str, Any],
    persisted: dict[str, Any],
    result: PlaygroundExecutionResult,
) -> dict[str, Any]:
    return {
        "session": session,
        "messages": [serialize_message(message) for message in persisted["messages"]],
        "output": result.output,
        "response": result.response,
        "sources": result.sources,
        "retrieval": result.retrieval,
    }


def _require_session(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
) -> dict[str, Any]:
    for conversation_kind in ("plain", "knowledge"):
        row = playgrounds_repository.get_session(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=session_id,
            conversation_kind=conversation_kind,
        )
        if row is not None:
            return row
    raise PlaygroundSessionNotFoundError


def _load_session_and_messages(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
    playground_kind: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if playground_kind:
        row = playgrounds_repository.get_session(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=session_id,
            conversation_kind=conversation_kind_for_playground_kind(playground_kind),
        )
        if row is None:
            raise PlaygroundSessionNotFoundError
    else:
        row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    messages = playgrounds_repository.list_messages(database_url, conversation_id=session_id)
    return row, messages


def _serialize_session_summary(row: dict[str, Any]) -> dict[str, Any]:
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))
    return {
        "id": str(row.get("id", "")),
        "playground_kind": playground_kind,
        "assistant_ref": string_or_none(row.get("assistant_ref")) or default_assistant_ref_for_kind(playground_kind),
        "title": str(row.get("title", _default_title_for_kind(playground_kind))),
        "title_source": str(row.get("title_source", DEFAULT_TITLE_SOURCE)),
        "model_selection": {"model_id": string_or_none(row.get("model_id"))},
        "knowledge_binding": {"knowledge_base_id": string_or_none(row.get("knowledge_base_id"))},
        "message_count": int(row.get("message_count") or 0),
        "created_at": serialize_datetime(row.get("created_at")),
        "updated_at": serialize_datetime(row.get("updated_at")),
    }


def _serialize_session_detail(
    row: dict[str, Any],
    messages: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    payload = _serialize_session_summary(row)
    payload["messages"] = [serialize_message(message) for message in messages]
    return payload


def _normalize_playground_kind(value: Any) -> str:
    normalized = str(value or CHAT_PLAYGROUND_KIND).strip().lower() or CHAT_PLAYGROUND_KIND
    if normalized not in {CHAT_PLAYGROUND_KIND, KNOWLEDGE_PLAYGROUND_KIND}:
        raise PlaygroundSessionValidationError("invalid_playground_kind", "playground_kind must be chat or knowledge")
    return normalized


def _normalize_title(value: Any) -> str:
    title = str(value or "").strip()
    if not title:
        raise PlaygroundSessionValidationError("invalid_title", "title is required")
    return title[:120]


def _normalize_assistant_ref(value: Any, *, playground_kind: str) -> str:
    normalized = str(value or "").strip()
    return normalized or default_assistant_ref_for_kind(playground_kind)


def _normalize_model_id(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("model_id")
    normalized = str(value or "").strip()
    return normalized or None


def _normalize_knowledge_base_id(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("knowledge_base_id")
    normalized = str(value or "").strip()
    return normalized or None


def _default_title_for_kind(playground_kind: str) -> str:
    if playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        return DEFAULT_KNOWLEDGE_TITLE
    return DEFAULT_CHAT_TITLE
