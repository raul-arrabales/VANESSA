from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.repositories import model_management


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._row


def test_get_model_by_id_returns_row(monkeypatch):
    expected_row = {
        "model_id": "phi-offline",
        "name": "Phi Offline",
        "backend_kind": "local",
    }
    captured: dict[str, object] = {}

    class _FakeConnection:
        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params
            return _FakeCursor(expected_row)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(model_management, "get_connection", _fake_get_connection)

    row = model_management.get_model_by_id("postgresql://ignored", "  phi-offline  ")

    assert row == expected_row
    assert captured["query"] == "SELECT * FROM model_registry WHERE model_id = %s"
    assert captured["params"] == ("phi-offline",)


def test_get_model_by_id_returns_none_when_missing(monkeypatch):
    class _FakeConnection:
        def execute(self, _query, _params):
            return _FakeCursor(None)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(model_management, "get_connection", _fake_get_connection)

    row = model_management.get_model_by_id("postgresql://ignored", "missing-model")

    assert row is None


def test_list_models_visible_to_user_includes_role_scope_assignments(monkeypatch):
    expected_rows = [{"model_id": "qwen-local"}]
    captured: dict[str, object] = {}

    class _FakeConnection:
        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params
            return _FakeCursor(expected_rows)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(model_management, "get_connection", _fake_get_connection)

    rows = model_management.list_models_visible_to_user(
        "postgresql://ignored",
        user_id=42,
        runtime_profile="OFFLINE",
    )

    query = str(captured["query"])
    params = captured["params"]
    assert rows == expected_rows
    assert "user_role_cte" in query
    assert "model_scope_assignments" in query
    assert "jsonb_array_elements_text(msa.model_ids)" in query
    assert "JOIN user_role_cte ur ON ur.role = msa.scope" in query
    assert "SELECT model_id FROM model_user_assignments WHERE user_id = %s" in query
    assert params == (42, 42, 42, 42, 42, "offline")


def test_list_models_visible_to_user_keeps_runtime_and_explicit_assignment_filters(monkeypatch):
    expected_rows = [{"model_id": "assigned-user-model"}]
    captured: dict[str, object] = {}

    class _FakeConnection:
        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params
            return _FakeCursor(expected_rows)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(model_management, "get_connection", _fake_get_connection)

    rows = model_management.list_models_visible_to_user(
        "postgresql://ignored",
        user_id=7,
        runtime_profile="online",
    )

    query = str(captured["query"])
    assert rows == expected_rows
    assert "m.is_enabled = TRUE" in query
    assert "(m.access_scope = 'assigned' AND a.model_id IS NOT NULL)" in query
    assert "SELECT model_id FROM model_global_assignments" in query
    assert "OR m.backend_kind = 'local'" in query
