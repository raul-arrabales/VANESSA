from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.repositories import chat_conversations


class _FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)
        self.rowcount = 0
        self.executed: list[tuple[str, object]] = []

    def execute(self, query, params=None):
        self.executed.append((str(query), params))
        self.rowcount = 1

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)

    def fetchall(self):
        rows = list(self._rows)
        self._rows.clear()
        return rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_conversation_scopes_by_owner(monkeypatch):
    expected_row = {
        "id": "conv-1",
        "owner_user_id": 42,
        "conversation_kind": "plain",
        "title": "Thread",
        "title_source": "auto",
        "model_id": "safe-small",
        "created_at": None,
        "updated_at": None,
        "message_count": 0,
    }
    captured: dict[str, object] = {}

    class _FakeConnection:
        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

            class _Result:
                def fetchone(self_inner):
                    return expected_row

            return _Result()

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(chat_conversations, "get_connection", _fake_get_connection)

    row = chat_conversations.get_conversation(
        "postgresql://ignored",
        owner_user_id=42,
        conversation_id="conv-1",
    )

    assert row == expected_row
    assert "WHERE c.id = %s AND c.owner_user_id = %s AND c.conversation_kind = %s" in str(captured["query"])
    assert captured["params"] == ("conv-1", 42, "plain")


def test_list_messages_orders_by_message_index(monkeypatch):
    expected_rows = [
        {"id": "msg-1", "message_index": 0, "role": "user", "content": "hello"},
        {"id": "msg-2", "message_index": 1, "role": "assistant", "content": "hi"},
    ]
    captured: dict[str, object] = {}

    class _FakeConnection:
        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

            class _Result:
                def fetchall(self_inner):
                    return expected_rows

            return _Result()

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(chat_conversations, "get_connection", _fake_get_connection)

    rows = chat_conversations.list_messages("postgresql://ignored", conversation_id="conv-1")

    assert rows == expected_rows
    assert "ORDER BY message_index ASC" in str(captured["query"])
    assert captured["params"] == ("conv-1",)


def test_delete_conversation_uses_owner_and_kind_scope(monkeypatch):
    fake_cursor = _FakeCursor([])

    class _FakeConnection:
        def cursor(self):
            return fake_cursor

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(chat_conversations, "get_connection", _fake_get_connection)

    deleted = chat_conversations.delete_conversation(
        "postgresql://ignored",
        owner_user_id=13,
        conversation_id="conv-9",
    )

    assert deleted is True
    assert "DELETE FROM chat_conversations" in fake_cursor.executed[0][0]
    assert fake_cursor.executed[0][1] == ("conv-9", 13, "plain")
