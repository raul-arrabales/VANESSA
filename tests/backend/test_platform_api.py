from __future__ import annotations

import pytest

from app.routes import platform as platform_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(platform_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(platform_routes, "_config", lambda: config)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_platform_capabilities_requires_auth(client):
    test_client, _ = client

    response = test_client.get("/v1/platform/capabilities")

    assert response.status_code == 401


def test_platform_capabilities_returns_active_provider_summary(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="user",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]
    monkeypatch.setattr(
        platform_routes,
        "list_capabilities",
        lambda _db, _config: [
            {
                "capability": "llm_inference",
                "display_name": "LLM inference",
                "description": "desc",
                "required": True,
                "active_provider": {
                    "id": "provider-1",
                    "slug": "vllm-local-gateway",
                    "provider_key": "vllm_local",
                    "display_name": "vLLM local gateway",
                    "deployment_profile_id": "deployment-1",
                    "deployment_profile_slug": "local-default",
                },
            }
        ],
    )

    response = test_client.get("/v1/platform/capabilities", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["capabilities"][0]["active_provider"]["slug"] == "vllm-local-gateway"


def test_platform_provider_and_deployment_routes_require_superadmin(client):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="user",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]

    providers = test_client.get("/v1/platform/providers", headers=_auth(token))
    deployments = test_client.get("/v1/platform/deployments", headers=_auth(token))
    activate = test_client.post("/v1/platform/deployments/deployment-1/activate", headers=_auth(token))

    assert providers.status_code == 403
    assert deployments.status_code == 403
    assert activate.status_code == 403


def test_superadmin_platform_management_routes_work(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    root = user_store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        platform_routes,
        "list_providers",
        lambda _db, _config: [
            {
                "id": "provider-1",
                "slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "capability": "llm_inference",
                "adapter_kind": "openai_compatible_llm",
                "display_name": "vLLM local gateway",
                "description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config": {},
            }
        ],
    )
    monkeypatch.setattr(
        platform_routes,
        "list_deployment_profiles",
        lambda _db, _config: [
            {
                "id": "deployment-1",
                "slug": "local-default",
                "display_name": "Local Default",
                "description": "desc",
                "is_active": True,
                "bindings": [],
            }
        ],
    )
    monkeypatch.setattr(
        platform_routes,
        "create_deployment_profile",
        lambda _db, *, config, payload, created_by_user_id: {
            "id": "deployment-2",
            "slug": payload["slug"],
            "display_name": payload["display_name"],
            "description": payload.get("description", ""),
            "is_active": False,
            "bindings": [],
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "activate_deployment_profile",
        lambda _db, *, config, deployment_profile_id, activated_by_user_id: {
            "id": deployment_profile_id,
            "slug": "staging-profile",
            "display_name": "Staging Profile",
            "description": "",
            "is_active": True,
            "bindings": [],
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "validate_provider",
        lambda _db, *, config, provider_instance_id: {
            "provider": {"id": provider_instance_id, "slug": "vllm-local-gateway"},
            "validation": {"health": {"reachable": True, "status_code": 200}},
        },
    )

    providers = test_client.get("/v1/platform/providers", headers=_auth(token))
    deployments = test_client.get("/v1/platform/deployments", headers=_auth(token))
    create_response = test_client.post(
        "/v1/platform/deployments",
        headers=_auth(token),
        json={
            "slug": "staging-profile",
            "display_name": "Staging Profile",
            "bindings": [],
        },
    )
    activate_response = test_client.post(
        "/v1/platform/deployments/deployment-2/activate",
        headers=_auth(token),
    )
    validate_response = test_client.post(
        "/v1/platform/providers/provider-1/validate",
        headers=_auth(token),
    )

    assert providers.status_code == 200
    assert providers.get_json()["providers"][0]["slug"] == "vllm-local-gateway"
    assert deployments.status_code == 200
    assert deployments.get_json()["deployments"][0]["is_active"] is True
    assert create_response.status_code == 201
    assert create_response.get_json()["deployment_profile"]["slug"] == "staging-profile"
    assert activate_response.status_code == 200
    assert activate_response.get_json()["deployment_profile"]["is_active"] is True
    assert validate_response.status_code == 200
    assert validate_response.get_json()["validation"]["health"]["reachable"] is True
