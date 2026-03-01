from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.repositories import registry


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


def test_upsert_runtime_profile_ensures_runtime_config_table(monkeypatch):
    executed: list[tuple[str, tuple | None]] = []

    class _FakeConnection:
        def execute(self, query, params=None):
            executed.append((query, params))
            return _FakeCursor(None)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(registry, "get_connection", _fake_get_connection)

    updated = registry.upsert_runtime_profile(
        "postgresql://ignored",
        profile="online",
        updated_by_user_id=7,
    )

    assert updated == "online"
    assert "CREATE TABLE IF NOT EXISTS system_runtime_config" in executed[0][0]
    assert "INSERT INTO system_runtime_config" in executed[1][0]
    assert executed[1][1] == ("online", 7)


def test_get_runtime_profile_ensures_runtime_config_table(monkeypatch):
    executed: list[tuple[str, tuple | None]] = []

    class _FakeConnection:
        def execute(self, query, params=None):
            executed.append((query, params))
            if "SELECT config_value FROM system_runtime_config" in query:
                return _FakeCursor({"config_value": "air_gapped"})
            return _FakeCursor(None)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(registry, "get_connection", _fake_get_connection)

    profile = registry.get_runtime_profile("postgresql://ignored")

    assert profile == "air_gapped"
    assert "CREATE TABLE IF NOT EXISTS system_runtime_config" in executed[0][0]
    assert "SELECT config_value FROM system_runtime_config" in executed[1][0]
