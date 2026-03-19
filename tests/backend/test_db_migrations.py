from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app import db


class _FakeCursor:
    def execute(self, _query, _params=None):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@contextmanager
def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
    yield _FakeConnection()


def test_run_auth_schema_migration_invokes_registry_migration(monkeypatch):
    call_order: list[str] = []

    monkeypatch.setattr(db, "get_connection", _fake_get_connection)
    monkeypatch.setattr(db, "run_registry_schema_migration", lambda _db: call_order.append("registry"))
    monkeypatch.setattr(db, "run_model_management_schema_migration", lambda _db: call_order.append("model_management"))
    monkeypatch.setattr(db, "run_platform_control_plane_schema_migration", lambda _db: call_order.append("platform"))
    monkeypatch.setattr(db, "run_quotes_schema_migration", lambda _db: call_order.append("quotes"))
    monkeypatch.setattr(db, "run_chat_conversations_schema_migration", lambda _db: call_order.append("chat"))

    db.run_auth_schema_migration("postgresql://ignored")

    assert call_order == ["registry", "model_management", "platform", "quotes", "chat"]
