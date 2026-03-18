from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services import chat_conversations as service  # noqa: E402


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _conversation_row(
    conversation_id: str,
    *,
    owner_user_id: int = 7,
    title: str = "New conversation",
    title_source: str = "auto",
    model_id: str | None = "safe-small",
) -> dict[str, object]:
    now = _now()
    return {
        "id": conversation_id,
        "owner_user_id": owner_user_id,
        "conversation_kind": "plain",
        "title": title,
        "title_source": title_source,
        "model_id": model_id,
        "created_at": now,
        "updated_at": now,
    }


def _install_fake_repo(monkeypatch: pytest.MonkeyPatch, *, conversations: dict[str, dict[str, object]], messages: dict[str, list[dict[str, object]]]) -> None:
    def _with_message_count(row: dict[str, object]) -> dict[str, object]:
        item = deepcopy(row)
        item["message_count"] = len(messages.get(str(row["id"]), []))
        return item

    def list_conversation_summaries(_database_url: str, *, owner_user_id: int, conversation_kind: str = "plain"):
        rows = [
            _with_message_count(row)
            for row in conversations.values()
            if int(row["owner_user_id"]) == owner_user_id and str(row["conversation_kind"]) == conversation_kind
        ]
        rows.sort(key=lambda row: row["updated_at"], reverse=True)
        return rows

    def get_conversation(_database_url: str, *, owner_user_id: int, conversation_id: str, conversation_kind: str = "plain"):
        row = conversations.get(conversation_id)
        if row is None:
            return None
        if int(row["owner_user_id"]) != owner_user_id or str(row["conversation_kind"]) != conversation_kind:
            return None
        return _with_message_count(row)

    def list_messages(_database_url: str, *, conversation_id: str):
        ordered = sorted(messages.get(conversation_id, []), key=lambda row: int(row["message_index"]))
        return [deepcopy(row) for row in ordered]

    def update_conversation(
        _database_url: str,
        *,
        owner_user_id: int,
        conversation_id: str,
        title: object = service.chat_repository._UNSET,
        title_source: object = service.chat_repository._UNSET,
        model_id: object = service.chat_repository._UNSET,
        conversation_kind: str = "plain",
    ):
        row = conversations.get(conversation_id)
        if row is None:
            return None
        if int(row["owner_user_id"]) != owner_user_id or str(row["conversation_kind"]) != conversation_kind:
            return None
        if title is not service.chat_repository._UNSET:
            row["title"] = title
        if title_source is not service.chat_repository._UNSET:
            row["title_source"] = title_source
        if model_id is not service.chat_repository._UNSET:
            row["model_id"] = model_id
        row["updated_at"] = _now()
        return _with_message_count(row)

    def delete_conversation(_database_url: str, *, owner_user_id: int, conversation_id: str, conversation_kind: str = "plain"):
        row = conversations.get(conversation_id)
        if row is None:
            return False
        if int(row["owner_user_id"]) != owner_user_id or str(row["conversation_kind"]) != conversation_kind:
            return False
        conversations.pop(conversation_id, None)
        messages.pop(conversation_id, None)
        return True

    def create_conversation(
        _database_url: str,
        *,
        owner_user_id: int,
        title: str,
        title_source: str,
        model_id: str | None,
        conversation_kind: str = "plain",
    ):
        conversation_id = str(uuid4())
        row = _conversation_row(
            conversation_id,
            owner_user_id=owner_user_id,
            title=title,
            title_source=title_source,
            model_id=model_id,
        )
        row["conversation_kind"] = conversation_kind
        conversations[conversation_id] = row
        messages[conversation_id] = []
        return _with_message_count(row)

    def append_message_pair(
        _database_url: str,
        *,
        owner_user_id: int,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
        user_metadata: dict | None = None,
        assistant_metadata: dict | None = None,
        conversation_title: str | None = None,
        title_source: str | None = None,
        conversation_kind: str = "plain",
    ):
        row = conversations.get(conversation_id)
        if row is None:
            return None
        if int(row["owner_user_id"]) != owner_user_id or str(row["conversation_kind"]) != conversation_kind:
            return None

        row["updated_at"] = _now()
        if conversation_title is not None:
            row["title"] = conversation_title
        if title_source is not None:
            row["title_source"] = title_source

        next_index = len(messages.get(conversation_id, []))
        user_message = {
            "id": str(uuid4()),
            "conversation_id": conversation_id,
            "message_index": next_index,
            "role": "user",
            "content": user_content,
            "metadata_json": user_metadata or {},
            "created_at": _now(),
        }
        assistant_message = {
            "id": str(uuid4()),
            "conversation_id": conversation_id,
            "message_index": next_index + 1,
            "role": "assistant",
            "content": assistant_content,
            "metadata_json": assistant_metadata or {},
            "created_at": _now(),
        }
        messages.setdefault(conversation_id, []).extend([user_message, assistant_message])
        return {
            "conversation": _with_message_count(row),
            "messages": [deepcopy(user_message), deepcopy(assistant_message)],
        }

    monkeypatch.setattr(service.chat_repository, "list_conversation_summaries", list_conversation_summaries)
    monkeypatch.setattr(service.chat_repository, "get_conversation", get_conversation)
    monkeypatch.setattr(service.chat_repository, "list_messages", list_messages)
    monkeypatch.setattr(service.chat_repository, "update_conversation", update_conversation)
    monkeypatch.setattr(service.chat_repository, "delete_conversation", delete_conversation)
    monkeypatch.setattr(service.chat_repository, "create_conversation", create_conversation)
    monkeypatch.setattr(service.chat_repository, "append_message_pair", append_message_pair)


def _llm_response(text: str) -> dict[str, object]:
    return {
        "output": [
            {
                "content": [
                    {"type": "text", "text": text},
                ],
            },
        ],
    }


def test_send_plain_message_auto_titles_first_message(monkeypatch: pytest.MonkeyPatch) -> None:
    conversations = {"conv-1": _conversation_row("conv-1")}
    messages: dict[str, list[dict[str, object]]] = {"conv-1": []}
    _install_fake_repo(monkeypatch, conversations=conversations, messages=messages)
    monkeypatch.setattr(
        service,
        "chat_completion_with_allowed_model",
        lambda **_kwargs: (_llm_response("Assistant reply"), 200),
    )

    result = service.send_plain_message(
        "postgresql://ignored",
        owner_user_id=7,
        conversation_id="conv-1",
        prompt="First thread message",
    )

    assert result["conversation"]["title"] == "First thread message"
    assert result["conversation"]["messageCount"] == 2
    assert [message["role"] for message in result["messages"]] == ["user", "assistant"]
    assert conversations["conv-1"]["title_source"] == "auto"


def test_send_plain_message_preserves_manual_title(monkeypatch: pytest.MonkeyPatch) -> None:
    conversations = {
        "conv-1": _conversation_row(
            "conv-1",
            title="Pinned title",
            title_source="manual",
        )
    }
    messages: dict[str, list[dict[str, object]]] = {"conv-1": []}
    _install_fake_repo(monkeypatch, conversations=conversations, messages=messages)
    monkeypatch.setattr(
        service,
        "chat_completion_with_allowed_model",
        lambda **_kwargs: (_llm_response("Assistant reply"), 200),
    )

    result = service.send_plain_message(
        "postgresql://ignored",
        owner_user_id=7,
        conversation_id="conv-1",
        prompt="New first message",
    )

    assert result["conversation"]["title"] == "Pinned title"
    assert conversations["conv-1"]["title"] == "Pinned title"
    assert conversations["conv-1"]["title_source"] == "manual"


def test_update_plain_conversation_marks_title_as_manual(monkeypatch: pytest.MonkeyPatch) -> None:
    conversations = {"conv-1": _conversation_row("conv-1")}
    messages: dict[str, list[dict[str, object]]] = {"conv-1": []}
    _install_fake_repo(monkeypatch, conversations=conversations, messages=messages)

    updated = service.update_plain_conversation(
        "postgresql://ignored",
        owner_user_id=7,
        conversation_id="conv-1",
        title="Renamed thread",
    )

    assert updated["title"] == "Renamed thread"
    assert updated["titleSource"] == "manual"
    assert conversations["conv-1"]["title"] == "Renamed thread"
    assert conversations["conv-1"]["title_source"] == "manual"
