from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.app import app  # noqa: E402
from app.services import auth_runtime  # noqa: E402


def test_ensure_backend_initialized_retries_platform_bootstrap_after_failure(monkeypatch: pytest.MonkeyPatch):
    bootstrap_calls: list[str] = []

    monkeypatch.setattr(auth_runtime, "_platform_bootstrapped", False)
    monkeypatch.setattr(auth_runtime, "ensure_auth_initialized", lambda: True)
    monkeypatch.setattr(auth_runtime, "get_config", lambda: SimpleNamespace(database_url="postgresql://ignored"))

    def _ensure_platform_bootstrap_state(_database_url: str, _config) -> None:
        bootstrap_calls.append("called")
        if len(bootstrap_calls) == 1:
            raise RuntimeError("runtime still starting")

    monkeypatch.setattr(auth_runtime, "ensure_platform_bootstrap_state", _ensure_platform_bootstrap_state)

    with app.app_context():
        assert auth_runtime.ensure_backend_initialized() is False
        assert auth_runtime.ensure_backend_initialized() is True

    assert bootstrap_calls == ["called", "called"]


def test_ensure_backend_initialized_stops_rebootstrapping_after_success(monkeypatch: pytest.MonkeyPatch):
    bootstrap_calls: list[str] = []

    monkeypatch.setattr(auth_runtime, "_platform_bootstrapped", False)
    monkeypatch.setattr(auth_runtime, "ensure_auth_initialized", lambda: True)
    monkeypatch.setattr(auth_runtime, "get_config", lambda: SimpleNamespace(database_url="postgresql://ignored"))
    monkeypatch.setattr(
        auth_runtime,
        "ensure_platform_bootstrap_state",
        lambda _database_url, _config: bootstrap_calls.append("called"),
    )

    with app.app_context():
        assert auth_runtime.ensure_backend_initialized() is True
        assert auth_runtime.ensure_backend_initialized() is True

    assert bootstrap_calls == ["called"]
