from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

import app.app as backend_app_module  # noqa: E402
from app.app import app  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_system_architecture_json_success(client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    architecture_path = tmp_path / "architecture.json"
    architecture_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "nodes": [{"id": "backend", "container": "backend", "label": "Backend", "group": "api", "description": "desc"}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(backend_app_module, "_ARCHITECTURE_JSON_PATH", architecture_path)

    response = client.get("/system/architecture")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == "1.0"
    assert payload["nodes"][0]["id"] == "backend"


def test_system_architecture_svg_success(client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    svg_path = tmp_path / "architecture.svg"
    svg_path.write_text("<svg><title>arch</title></svg>\n", encoding="utf-8")
    monkeypatch.setattr(backend_app_module, "_ARCHITECTURE_SVG_PATH", svg_path)

    response = client.get("/system/architecture.svg")

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert "<svg>" in response.get_data(as_text=True)


def test_system_architecture_missing_artifacts_return_503(client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing_json = tmp_path / "missing.json"
    missing_svg = tmp_path / "missing.svg"
    monkeypatch.setattr(backend_app_module, "_ARCHITECTURE_JSON_PATH", missing_json)
    monkeypatch.setattr(backend_app_module, "_ARCHITECTURE_SVG_PATH", missing_svg)

    json_response = client.get("/system/architecture")
    svg_response = client.get("/system/architecture.svg")

    assert json_response.status_code == 503
    assert json_response.get_json()["error"] == "architecture_unavailable"
    assert svg_response.status_code == 503
    assert svg_response.get_json()["error"] == "architecture_unavailable"
