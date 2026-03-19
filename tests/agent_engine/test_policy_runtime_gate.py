from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services import policy_runtime_gate  # noqa: E402


def test_resolve_runtime_profile_prefers_requested_profile(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        policy_runtime_gate,
        "get_config",
        lambda: type("Config", (), {"database_url": "", "runtime_profile_force": "offline"})(),
    )

    assert policy_runtime_gate.resolve_runtime_profile("online") == "online"


def test_resolve_runtime_profile_uses_forced_env_before_db(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        policy_runtime_gate,
        "get_config",
        lambda: type("Config", (), {"database_url": "postgresql://ignored", "runtime_profile_force": "offline"})(),
    )

    assert policy_runtime_gate.resolve_runtime_profile(None) == "offline"


def test_resolve_runtime_profile_uses_db_when_not_forced(monkeypatch: pytest.MonkeyPatch):
    class _FakeConnection:
        def execute(self, _query, _params=None):
            return type("Cursor", (), {"fetchone": lambda self: {"config_value": "online"}})()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        policy_runtime_gate,
        "get_config",
        lambda: type("Config", (), {"database_url": "postgresql://ignored", "runtime_profile_force": None})(),
    )
    monkeypatch.setattr(policy_runtime_gate, "psycopg", type("Psycopg", (), {"connect": lambda *args, **kwargs: _FakeConnection()})())
    monkeypatch.setattr(policy_runtime_gate, "dict_row", object())

    assert policy_runtime_gate.resolve_runtime_profile(None) == "online"


def test_resolve_runtime_profile_normalizes_legacy_air_gapped_db_value(monkeypatch: pytest.MonkeyPatch):
    class _FakeConnection:
        def execute(self, _query, _params=None):
            return type("Cursor", (), {"fetchone": lambda self: {"config_value": "air_gapped"}})()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        policy_runtime_gate,
        "get_config",
        lambda: type("Config", (), {"database_url": "postgresql://ignored", "runtime_profile_force": None})(),
    )
    monkeypatch.setattr(policy_runtime_gate, "psycopg", type("Psycopg", (), {"connect": lambda *args, **kwargs: _FakeConnection()})())
    monkeypatch.setattr(policy_runtime_gate, "dict_row", object())

    assert policy_runtime_gate.resolve_runtime_profile(None) == "offline"
