from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

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
    monkeypatch.setattr(db, "run_context_management_schema_migration", lambda _db: call_order.append("context"))
    monkeypatch.setattr(db, "run_modelops_schema_migration", lambda _db: call_order.append("modelops"))
    monkeypatch.setattr(db, "run_modelops_testing_schema_migration", lambda _db: call_order.append("modelops_testing"))
    monkeypatch.setattr(db, "run_quotes_schema_migration", lambda _db: call_order.append("quotes"))
    monkeypatch.setattr(db, "run_chat_conversations_schema_migration", lambda _db: call_order.append("chat"))

    db.run_auth_schema_migration("postgresql://ignored")

    assert call_order == [
        "registry",
        "model_management",
        "platform",
        "context",
        "modelops",
        "modelops_testing",
        "quotes",
        "chat",
    ]


def test_run_platform_control_plane_schema_migration_executes_base_and_additive_sql(monkeypatch):
    executed_sql: list[str] = []

    class _RecordingCursor(_FakeCursor):
        def execute(self, query, _params=None):
            executed_sql.append(str(query))
            return None

    class _RecordingConnection(_FakeConnection):
        def cursor(self):
            return _RecordingCursor()

    @contextmanager
    def _recording_get_connection(_database_url: str) -> Iterator[_RecordingConnection]:
        yield _RecordingConnection()

    migration_sql_by_name = {
        "006_platform_control_plane.sql": "-- migration 006",
        "011_platform_binding_resources.sql": "-- migration 011",
    }
    original_read_text = Path.read_text

    def _fake_read_text(self: Path, encoding: str = "utf-8") -> str:
        del encoding
        if self.name in migration_sql_by_name:
            return migration_sql_by_name[self.name]
        return original_read_text(self, encoding="utf-8")

    monkeypatch.setattr(db, "get_connection", _recording_get_connection)
    monkeypatch.setattr(Path, "read_text", _fake_read_text)

    db.run_platform_control_plane_schema_migration("postgresql://ignored")

    assert executed_sql == ["-- migration 006", "-- migration 011"]


def test_run_context_management_schema_migration_executes_context_sql(monkeypatch):
    executed_sql: list[str] = []

    class _RecordingCursor(_FakeCursor):
        def execute(self, query, _params=None):
            executed_sql.append(str(query))
            return None

    class _RecordingConnection(_FakeConnection):
        def cursor(self):
            return _RecordingCursor()

    @contextmanager
    def _recording_get_connection(_database_url: str) -> Iterator[_RecordingConnection]:
        yield _RecordingConnection()

    original_read_text = Path.read_text

    def _fake_read_text(self: Path, encoding: str = "utf-8") -> str:
        del encoding
        if self.name == "012_context_management.sql":
            return "-- migration 012"
        if self.name == "013_context_management_ops.sql":
            return "-- migration 013"
        return original_read_text(self, encoding="utf-8")

    monkeypatch.setattr(db, "get_connection", _recording_get_connection)
    monkeypatch.setattr(Path, "read_text", _fake_read_text)

    db.run_context_management_schema_migration("postgresql://ignored")

    assert executed_sql == ["-- migration 012", "-- migration 013"]


def test_platform_binding_resources_migration_guards_legacy_copy_when_table_absent():
    migration_file = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "postgres"
        / "init"
        / "011_platform_binding_resources.sql"
    )
    migration_sql = migration_file.read_text(encoding="utf-8")

    assert "to_regclass('public.platform_binding_served_models') IS NOT NULL" in migration_sql
    assert "DROP TABLE IF EXISTS platform_binding_served_models;" in migration_sql
