from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.repositories import context_management


class _FakeResult:
    def __init__(self, *, many=None):
        self._many = list(many or [])

    def fetchall(self):
        return list(self._many)


def test_list_sync_runs_qualifies_knowledge_base_id_filter(monkeypatch):
    captured: dict[str, object] = {}
    expected_rows = [
        {
            "id": "run-1",
            "knowledge_base_id": "kb-primary",
            "source_id": "source-1",
            "source_display_name": "Docs folder",
            "status": "ready",
        }
    ]

    class _FakeConnection:
        def execute(self, query, params=None):
            captured["query"] = str(query)
            captured["params"] = params
            return _FakeResult(many=expected_rows)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(context_management, "get_connection", _fake_get_connection)

    rows = context_management.list_sync_runs("postgresql://ignored", knowledge_base_id="kb-primary")

    assert rows == expected_rows
    assert "sources.display_name AS source_display_name" in captured["query"]
    assert "WHERE runs.knowledge_base_id = %s" in captured["query"]
    assert captured["params"] == ("kb-primary",)
