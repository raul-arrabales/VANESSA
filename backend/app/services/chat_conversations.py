from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime
from typing import Any

from .chat_inference import (
    chat_completion_stream_with_allowed_model,
    chat_completion_with_allowed_model,
    extract_output_text,
)
from ..repositories import chat_conversations as chat_repository

DEFAULT_CONVERSATION_TITLE = "New conversation"
DEFAULT_TITLE_SOURCE = "auto"
MAX_CONTEXT_MESSAGES = 14
CONTEXT_CHAR_BUDGET = 8000
CHAT_CONVERSATION_UNSET = object()


class ChatConversationValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ChatConversationNotFoundError(Exception):
    pass


class ChatConversationInferenceError(Exception):
    def __init__(self, payload: dict[str, Any], status_code: int):
        super().__init__(payload.get("message") or payload.get("error") or "chat_inference_failed")
        self.payload = payload
        self.status_code = status_code


def list_plain_conversations(database_url: str, *, owner_user_id: int) -> list[dict[str, Any]]:
    rows = chat_repository.list_conversation_summaries(
        database_url,
        owner_user_id=owner_user_id,
    )
    return [serialize_conversation_summary(row) for row in rows]


def create_plain_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    model_id: Any = None,
) -> dict[str, Any]:
    conversation = chat_repository.create_conversation(
        database_url,
        owner_user_id=owner_user_id,
        title=DEFAULT_CONVERSATION_TITLE,
        title_source=DEFAULT_TITLE_SOURCE,
        model_id=_normalize_model_id(model_id),
    )
    return serialize_conversation_detail(conversation, [])


def get_plain_conversation_detail(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
) -> dict[str, Any]:
    conversation = _require_plain_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
    )
    messages = chat_repository.list_messages(database_url, conversation_id=conversation_id)
    return serialize_conversation_detail(conversation, messages)


def update_plain_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    title: object = CHAT_CONVERSATION_UNSET,
    model_id: object = CHAT_CONVERSATION_UNSET,
) -> dict[str, Any]:
    update_title = CHAT_CONVERSATION_UNSET
    update_title_source = CHAT_CONVERSATION_UNSET
    update_model_id = CHAT_CONVERSATION_UNSET

    if title is not CHAT_CONVERSATION_UNSET:
        update_title = _normalize_title(title)
        update_title_source = "manual"
    if model_id is not CHAT_CONVERSATION_UNSET:
        update_model_id = _normalize_model_id(model_id)

    updated = chat_repository.update_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        title=update_title,
        title_source=update_title_source,
        model_id=update_model_id,
    )
    if updated is None:
        raise ChatConversationNotFoundError
    return serialize_conversation_summary(updated)


def delete_plain_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
) -> None:
    deleted = chat_repository.delete_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
    )
    if not deleted:
        raise ChatConversationNotFoundError


def send_plain_message(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    prompt: Any,
) -> dict[str, Any]:
    prepared = _prepare_plain_message_request(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        prompt=prompt,
    )

    llm_response, status_code = chat_completion_with_allowed_model(
        requested_model_id=prepared["model_id"],
        org_id=None,
        group_id=None,
        messages=prepared["llm_messages"],
        max_tokens=None,
        temperature=None,
    )
    if llm_response is None:
        raise ChatConversationInferenceError(
            {"error": "llm_unreachable", "message": "LLM service unavailable"},
            502,
        )
    if status_code >= 400:
        raise ChatConversationInferenceError(
            llm_response if isinstance(llm_response, dict) else {"error": "chat_inference_failed"},
            status_code,
        )

    assistant_output = extract_output_text(llm_response)
    if not assistant_output:
        raise ChatConversationInferenceError(
            {"error": "empty_response", "message": "LLM stream completed without assistant output"},
            502,
        )

    persisted = chat_repository.append_message_pair(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        user_content=prepared["prompt_text"],
        assistant_content=assistant_output,
        conversation_title=prepared["conversation_title"],
        title_source=prepared["title_source"],
    )
    if persisted is None:
        raise ChatConversationNotFoundError

    return {
        "conversation": serialize_conversation_summary(persisted["conversation"]),
        "messages": [serialize_message(message) for message in persisted["messages"]],
        "output": assistant_output,
        "response": llm_response,
    }


def stream_plain_message(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    prompt: Any,
) -> Iterator[dict[str, Any]]:
    prepared = _prepare_plain_message_request(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        prompt=prompt,
    )
    stream, error_payload, status_code = chat_completion_stream_with_allowed_model(
        requested_model_id=prepared["model_id"],
        org_id=None,
        group_id=None,
        messages=prepared["llm_messages"],
        max_tokens=None,
        temperature=None,
    )
    if error_payload is not None or stream is None:
        raise ChatConversationInferenceError(
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
                        "error": "chat_inference_failed",
                        "message": "LLM stream failed",
                    }
                yield {
                    "event": "error",
                    "data": {
                        "error": str(payload.get("error") or "chat_inference_failed"),
                        "message": str(payload.get("message") or "LLM stream failed"),
                    },
                }
                return

            if event_type != "complete":
                continue

            llm_response = event.get("response")
            if not isinstance(llm_response, dict):
                llm_response = {"output": [{"content": [{"type": "text", "text": "".join(assistant_output_parts)}]}]}

            assistant_output = extract_output_text(llm_response) or "".join(assistant_output_parts)
            if not assistant_output:
                yield {
                    "event": "error",
                    "data": {
                        "error": "empty_response",
                        "message": "LLM stream completed without assistant output",
                    },
                }
                return

            persisted = chat_repository.append_message_pair(
                database_url,
                owner_user_id=owner_user_id,
                conversation_id=conversation_id,
                user_content=prepared["prompt_text"],
                assistant_content=assistant_output,
                conversation_title=prepared["conversation_title"],
                title_source=prepared["title_source"],
            )
            if persisted is None:
                yield {
                    "event": "error",
                    "data": {
                        "error": "conversation_not_found",
                        "message": "Conversation not found",
                    },
                }
                return

            yield {
                "event": "complete",
                "data": {
                    "conversation": serialize_conversation_summary(persisted["conversation"]),
                    "messages": [serialize_message(message) for message in persisted["messages"]],
                    "output": assistant_output,
                    "response": llm_response,
                },
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


def serialize_conversation_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "title": str(row.get("title", DEFAULT_CONVERSATION_TITLE)),
        "titleSource": str(row.get("title_source", DEFAULT_TITLE_SOURCE)),
        "modelId": _string_or_none(row.get("model_id")),
        "messageCount": int(row.get("message_count") or 0),
        "createdAt": _serialize_datetime(row.get("created_at")),
        "updatedAt": _serialize_datetime(row.get("updated_at")),
    }


def serialize_message(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata_json")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "id": str(row.get("id", "")),
        "role": str(row.get("role", "")),
        "content": str(row.get("content", "")),
        "metadata": metadata,
        "createdAt": _serialize_datetime(row.get("created_at")),
    }


def serialize_conversation_detail(
    row: dict[str, Any],
    messages: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    payload = serialize_conversation_summary(row)
    payload["messages"] = [serialize_message(message) for message in messages]
    return payload


def _require_plain_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
) -> dict[str, Any]:
    conversation = chat_repository.get_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
    )
    if conversation is None:
        raise ChatConversationNotFoundError
    return conversation


def _prepare_plain_message_request(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    prompt: Any,
) -> dict[str, Any]:
    prompt_text = _normalize_prompt(prompt)
    conversation = _require_plain_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
    )
    model_id = str(conversation.get("model_id") or "").strip()
    if not model_id:
        raise ChatConversationValidationError(
            "invalid_model_id",
            "Conversation model_id is required before sending messages",
        )

    existing_messages = chat_repository.list_messages(database_url, conversation_id=conversation_id)
    llm_messages = _build_context_messages(existing_messages)
    llm_messages.append(
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}],
        }
    )

    conversation_title = None
    title_source = None
    if not existing_messages and str(conversation.get("title_source") or DEFAULT_TITLE_SOURCE) == DEFAULT_TITLE_SOURCE:
        conversation_title = _auto_title_from_prompt(prompt_text)
        title_source = DEFAULT_TITLE_SOURCE

    return {
        "prompt_text": prompt_text,
        "conversation": conversation,
        "conversation_id": conversation_id,
        "model_id": model_id,
        "existing_messages": existing_messages,
        "llm_messages": llm_messages,
        "conversation_title": conversation_title,
        "title_source": title_source,
    }


def _normalize_prompt(value: Any) -> str:
    prompt = str(value or "").strip()
    if not prompt:
        raise ChatConversationValidationError("invalid_prompt", "prompt is required")
    return prompt


def _normalize_title(value: Any) -> str:
    title = str(value or "").strip()
    if not title:
        raise ChatConversationValidationError("invalid_title", "title is required")
    return title[:120]


def _normalize_model_id(value: Any) -> str | None:
    model_id = str(value or "").strip()
    return model_id or None


def _auto_title_from_prompt(prompt: str) -> str:
    return prompt[:64] or DEFAULT_CONVERSATION_TITLE


def _build_context_messages(messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
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

    return [
        {
            "role": str(message.get("role") or ""),
            "content": [{"type": "text", "text": str(message.get("content") or "")}],
        }
        for message in reversed(selected)
    ]


def _serialize_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value is not None else None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
