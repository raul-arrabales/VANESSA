from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime
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
from ..services import chat_conversations as chat_service
from ..services.knowledge_chat_service import (
    list_knowledge_chat_knowledge_bases,
    run_knowledge_chat,
)
from ..services.modelops_queries import list_models

DEFAULT_TITLE_SOURCE = "auto"
DEFAULT_CHAT_TITLE = "New chat session"
DEFAULT_KNOWLEDGE_TITLE = "New knowledge session"
SESSION_UNSET = object()


class PlaygroundSessionValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class PlaygroundSessionNotFoundError(Exception):
    pass


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
    row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))

    if playground_kind == CHAT_PLAYGROUND_KIND:
        response_payload = chat_service.send_plain_message(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=session_id,
            prompt=prompt,
        )
        session = get_playground_session_detail(
            database_url,
            owner_user_id=owner_user_id,
            session_id=session_id,
            playground_kind=CHAT_PLAYGROUND_KIND,
        )
        return {
            "session": session,
            "messages": response_payload["messages"],
            "output": response_payload["output"],
            "response": response_payload.get("response"),
        }

    return _send_knowledge_message(
        database_url,
        config=config,
        request_id=request_id,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        row=row,
        prompt=prompt,
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
    row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))

    if playground_kind == CHAT_PLAYGROUND_KIND:
        for event in chat_service.stream_plain_message(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=session_id,
            prompt=prompt,
        ):
            if str(event.get("event")) == "complete":
                session = get_playground_session_detail(
                    database_url,
                    owner_user_id=owner_user_id,
                    session_id=session_id,
                    playground_kind=CHAT_PLAYGROUND_KIND,
                )
                data = dict(event.get("data") or {})
                data["session"] = session
                yield {"event": "complete", "data": data}
                return
            yield event
        return

    payload = send_playground_message(
        database_url,
        config=config,
        request_id=request_id,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        session_id=session_id,
        prompt=prompt,
    )
    yield {"event": "complete", "data": payload}


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
    knowledge_payload, _status_code = list_knowledge_chat_knowledge_bases(
        database_url=database_url,
        config=config,
    )
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


def _send_knowledge_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    row: dict[str, Any],
    prompt: Any,
) -> dict[str, Any]:
    prompt_text = chat_service._normalize_prompt(prompt)
    history_messages = playgrounds_repository.list_messages(database_url, conversation_id=str(row["id"]))
    history = [
        {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
        for item in history_messages
    ]

    knowledge_base_id = _string_or_none(row.get("knowledge_base_id"))
    if not knowledge_base_id:
        raise PlaygroundSessionValidationError(
            "knowledge_base_required",
            "knowledge_binding.knowledge_base_id is required for knowledge playground sessions",
        )
    model_id = _string_or_none(row.get("model_id"))
    if not model_id:
        raise PlaygroundSessionValidationError(
            "invalid_model_id",
            "model_selection.model_id is required before sending messages",
        )

    response_payload, status_code = run_knowledge_chat(
        database_url=database_url,
        config=config,
        request_id=request_id,
        prompt=prompt_text,
        requested_model_id=model_id,
        requested_knowledge_base_id=knowledge_base_id,
        history_payload=history,
        actor_user_id=owner_user_id,
        actor_user_role=owner_role,
    )
    if status_code >= 400:
        raise PlaygroundSessionValidationError(
            str(response_payload.get("error", "knowledge_chat_failed")),
            str(response_payload.get("message", "Knowledge chat request failed.")),
        )

    conversation_title = None
    title_source = None
    if not history_messages and str(row.get("title_source") or DEFAULT_TITLE_SOURCE) == DEFAULT_TITLE_SOURCE:
        conversation_title = chat_service._auto_title_from_prompt(prompt_text)
        title_source = DEFAULT_TITLE_SOURCE

    persisted = playgrounds_repository.append_message_pair(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=str(row["id"]),
        user_content=prompt_text,
        assistant_content=str(response_payload.get("output", "")),
        assistant_metadata={
            "response": response_payload.get("response"),
            "sources": response_payload.get("sources", []),
            "retrieval": response_payload.get("retrieval"),
            "knowledge_base_id": response_payload.get("knowledge_base_id"),
        },
        conversation_title=conversation_title,
        title_source=title_source,
        conversation_kind=str(row.get("conversation_kind", "")),
    )
    if persisted is None:
        raise PlaygroundSessionNotFoundError

    session = get_playground_session_detail(
        database_url,
        owner_user_id=owner_user_id,
        session_id=str(row["id"]),
        playground_kind=KNOWLEDGE_PLAYGROUND_KIND,
    )
    return {
        "session": session,
        "messages": [chat_service.serialize_message(message) for message in persisted["messages"]],
        "output": str(response_payload.get("output", "")),
        "response": response_payload.get("response"),
        "sources": response_payload.get("sources", []),
        "retrieval": response_payload.get("retrieval"),
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
        "assistant_ref": _string_or_none(row.get("assistant_ref")) or default_assistant_ref_for_kind(playground_kind),
        "title": str(row.get("title", _default_title_for_kind(playground_kind))),
        "title_source": str(row.get("title_source", DEFAULT_TITLE_SOURCE)),
        "model_selection": {"model_id": _string_or_none(row.get("model_id"))},
        "knowledge_binding": {"knowledge_base_id": _string_or_none(row.get("knowledge_base_id"))},
        "message_count": int(row.get("message_count") or 0),
        "created_at": _serialize_datetime(row.get("created_at")),
        "updated_at": _serialize_datetime(row.get("updated_at")),
    }


def _serialize_session_detail(
    row: dict[str, Any],
    messages: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    payload = _serialize_session_summary(row)
    payload["messages"] = [chat_service.serialize_message(message) for message in messages]
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


def _serialize_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value is not None else None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
