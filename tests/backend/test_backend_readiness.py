from __future__ import annotations

from pathlib import Path

import pytest

import app.app as backend_app_module  # noqa: E402
import app.bootstrap as backend_bootstrap_module  # noqa: E402
from app.app import app  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health_route_reports_ready_after_backend_initialization(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(backend_app_module, "_ensure_backend_initialized", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "backend"}


def test_health_route_reports_503_when_backend_initialization_is_not_ready(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(backend_app_module, "_ensure_backend_initialized", lambda: False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {
        "status": "initializing",
        "service": "backend",
        "ready": False,
        "message": "Backend initialization is still in progress.",
    }


def test_unauthenticated_request_triggers_backend_initialization_before_auth_short_circuit(
    client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    calls: list[str] = []
    architecture_path = tmp_path / "architecture.json"
    architecture_path.write_text(
        '{"version":"1.0","generated_at":"2026-01-01T00:00:00+00:00","nodes":[],"edges":[]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(backend_bootstrap_module, "_ARCHITECTURE_JSON_PATH", architecture_path)
    monkeypatch.setattr(
        backend_app_module,
        "_ensure_backend_initialized",
        lambda: calls.append("initialized") or True,
    )

    response = client.get("/system/architecture")

    assert response.status_code == 200
    assert calls == ["initialized"]
