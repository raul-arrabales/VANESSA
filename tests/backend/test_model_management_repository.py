from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.repositories import model_management


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
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
