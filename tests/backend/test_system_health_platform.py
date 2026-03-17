from __future__ import annotations

import pytest

import app.app as backend_app_module  # noqa: E402
from app.app import app  # noqa: E402
from tests.backend.support.auth_harness import build_test_auth_config  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_system_health_includes_platform_capabilities(client, monkeypatch: pytest.MonkeyPatch):
    config = build_test_auth_config(backend_app_module.AuthConfig)
    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(backend_app_module, "_http_json_ok", lambda _url: True)
    monkeypatch.setattr(backend_app_module, "_postgres_ok", lambda _db: True)
    monkeypatch.setattr(
        backend_app_module,
        "get_active_capability_statuses",
        lambda _db, _config: [
            {
                "capability": "llm_inference",
                "provider": {
                    "id": "provider-1",
                    "slug": "vllm-local-gateway",
                    "provider_key": "vllm_local",
                    "display_name": "vLLM local gateway",
                },
                "deployment_profile": {
                    "id": "deployment-1",
                    "slug": "local-default",
                    "display_name": "Local Default",
                },
                "health": {"reachable": True, "status_code": 200},
            }
        ],
    )

    response = client.get("/system/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["platform"]["capabilities"][0]["capability"] == "llm_inference"
    assert payload["platform"]["capabilities"][0]["provider"]["slug"] == "vllm-local-gateway"


def test_system_health_includes_llama_cpp_service_when_configured(client, monkeypatch: pytest.MonkeyPatch):
    config = build_test_auth_config(backend_app_module.AuthConfig, llama_cpp_url="http://llama_cpp:8080")
    seen_urls: list[str] = []

    def _http_ok(url: str) -> bool:
        seen_urls.append(url)
        return True

    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(backend_app_module, "_http_json_ok", _http_ok)
    monkeypatch.setattr(backend_app_module, "_postgres_ok", lambda _db: True)
    monkeypatch.setattr(backend_app_module, "get_active_capability_statuses", lambda _db, _config: [])

    response = client.get("/system/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert any(service["container"] == "llama_cpp" for service in payload["services"])
    assert "http://llama_cpp:8080/v1/models" in seen_urls


def test_system_health_includes_qdrant_service_when_configured(client, monkeypatch: pytest.MonkeyPatch):
    config = build_test_auth_config(backend_app_module.AuthConfig, qdrant_url="http://qdrant:6333")
    seen_urls: list[str] = []

    def _http_ok(url: str) -> bool:
        seen_urls.append(url)
        return True

    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(backend_app_module, "_http_json_ok", _http_ok)
    monkeypatch.setattr(backend_app_module, "_postgres_ok", lambda _db: True)
    monkeypatch.setattr(backend_app_module, "get_active_capability_statuses", lambda _db, _config: [])

    response = client.get("/system/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert any(service["container"] == "qdrant" for service in payload["services"])
    assert "http://qdrant:6333/healthz" in seen_urls
