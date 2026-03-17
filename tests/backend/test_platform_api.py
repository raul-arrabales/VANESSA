from __future__ import annotations

import pytest

from app.routes import platform as platform_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402
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
    provider_families = test_client.get("/v1/platform/provider-families", headers=_auth(token))
    activation_audit = test_client.get("/v1/platform/activation-audit", headers=_auth(token))
    create_provider = test_client.post("/v1/platform/providers", headers=_auth(token), json={})
    update_provider = test_client.put("/v1/platform/providers/provider-1", headers=_auth(token), json={})
    delete_provider = test_client.delete("/v1/platform/providers/provider-1", headers=_auth(token))
    deployments = test_client.get("/v1/platform/deployments", headers=_auth(token))
    update_deployment = test_client.put("/v1/platform/deployments/deployment-1", headers=_auth(token), json={})
    clone_deployment = test_client.post("/v1/platform/deployments/deployment-1/clone", headers=_auth(token), json={})
    activate = test_client.post("/v1/platform/deployments/deployment-1/activate", headers=_auth(token))
    delete_deployment = test_client.delete("/v1/platform/deployments/deployment-1", headers=_auth(token))
    ensure_index = test_client.post("/v1/platform/vector/indexes/ensure", headers=_auth(token), json={"index": "kb"})
    upsert_documents = test_client.post(
        "/v1/platform/vector/documents/upsert",
        headers=_auth(token),
        json={"index": "kb", "documents": [{"id": "doc-1", "text": "hello"}]},
    )
    query_documents = test_client.post(
        "/v1/platform/vector/query",
        headers=_auth(token),
        json={"index": "kb", "query_text": "hello"},
    )
    delete_documents = test_client.post(
        "/v1/platform/vector/documents/delete",
        headers=_auth(token),
        json={"index": "kb", "ids": ["doc-1"]},
    )

    assert providers.status_code == 403
    assert provider_families.status_code == 403
    assert activation_audit.status_code == 403
    assert create_provider.status_code == 403
    assert update_provider.status_code == 403
    assert delete_provider.status_code == 403
    assert deployments.status_code == 403
    assert update_deployment.status_code == 403
    assert clone_deployment.status_code == 403
    assert activate.status_code == 403
    assert delete_deployment.status_code == 403
    assert ensure_index.status_code == 403
    assert upsert_documents.status_code == 403
    assert query_documents.status_code == 403
    assert delete_documents.status_code == 403


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
        "list_provider_families",
        lambda _db, _config: [
            {
                "provider_key": "vllm_local",
                "capability": "llm_inference",
                "adapter_kind": "openai_compatible_llm",
                "display_name": "vLLM local gateway",
                "description": "desc",
            }
        ],
    )
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
                "secret_refs": {},
            }
        ],
    )
    monkeypatch.setattr(
        platform_routes,
        "create_provider",
        lambda _db, *, config, payload: {
            "id": "provider-2",
            "slug": payload["slug"],
            "provider_key": payload["provider_key"],
            "capability": "llm_inference",
            "adapter_kind": "openai_compatible_llm",
            "display_name": payload["display_name"],
            "description": payload.get("description", ""),
            "endpoint_url": payload["endpoint_url"],
            "healthcheck_url": payload.get("healthcheck_url"),
            "enabled": payload.get("enabled", True),
            "config": payload.get("config", {}),
            "secret_refs": payload.get("secret_refs", {}),
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "update_provider",
        lambda _db, *, config, provider_instance_id, payload: {
            "id": provider_instance_id,
            "slug": payload["slug"],
            "provider_key": "vllm_local",
            "capability": "llm_inference",
            "adapter_kind": "openai_compatible_llm",
            "display_name": payload["display_name"],
            "description": payload.get("description", ""),
            "endpoint_url": payload["endpoint_url"],
            "healthcheck_url": payload.get("healthcheck_url"),
            "enabled": payload.get("enabled", True),
            "config": payload.get("config", {}),
            "secret_refs": payload.get("secret_refs", {}),
        },
    )
    monkeypatch.setattr(platform_routes, "delete_provider", lambda _db, *, config, provider_instance_id: None)
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
        "list_deployment_activation_audit",
        lambda _db, _config: [
            {
                "id": "audit-1",
                "deployment_profile": {
                    "id": "deployment-1",
                    "slug": "local-default",
                    "display_name": "Local Default",
                },
                "previous_deployment_profile": None,
                "activated_by_user_id": 1,
                "activated_at": "2026-01-01T00:00:00+00:00",
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
        "update_deployment_profile",
        lambda _db, *, config, deployment_profile_id, payload, updated_by_user_id: {
            "id": deployment_profile_id,
            "slug": payload["slug"],
            "display_name": payload["display_name"],
            "description": payload.get("description", ""),
            "is_active": False,
            "bindings": [],
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "clone_deployment_profile",
        lambda _db, *, config, source_deployment_profile_id, payload, created_by_user_id: {
            "id": "deployment-3",
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
    monkeypatch.setattr(platform_routes, "delete_deployment_profile", lambda _db, *, config, deployment_profile_id: None)
    monkeypatch.setattr(
        platform_routes,
        "validate_provider",
        lambda _db, *, config, provider_instance_id: {
            "provider": {"id": provider_instance_id, "slug": "vllm-local-gateway"},
            "validation": {"health": {"reachable": True, "status_code": 200}},
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "ensure_vector_index",
        lambda _db, _config, payload: {
            "index": {"name": payload["index"], "provider": "weaviate-local", "status": "ready", "created": True}
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "upsert_vector_documents",
        lambda _db, _config, payload: {
            "index": payload["index"],
            "count": len(payload["documents"]),
            "documents": [{"id": payload["documents"][0]["id"], "status": "upserted"}],
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "query_vector_documents",
        lambda _db, _config, payload: {
            "index": payload["index"],
            "results": [{"id": "doc-1", "text": "hello", "metadata": {}, "score": 0.1, "score_kind": "distance"}],
        },
    )
    monkeypatch.setattr(
        platform_routes,
        "delete_vector_documents",
        lambda _db, _config, payload: {
            "index": payload["index"],
            "count": len(payload["ids"]),
            "deleted_ids": list(payload["ids"]),
        },
    )

    providers = test_client.get("/v1/platform/providers", headers=_auth(token))
    provider_families = test_client.get("/v1/platform/provider-families", headers=_auth(token))
    activation_audit = test_client.get("/v1/platform/activation-audit", headers=_auth(token))
    create_provider_response = test_client.post(
        "/v1/platform/providers",
        headers=_auth(token),
        json={
            "provider_key": "vllm_local",
            "slug": "custom-vllm",
            "display_name": "Custom vLLM",
            "endpoint_url": "http://llm-alt:8000",
            "enabled": True,
            "config": {},
            "secret_refs": {"api_key": "env://VLLM_API_KEY"},
        },
    )
    update_provider_response = test_client.put(
        "/v1/platform/providers/provider-1",
        headers=_auth(token),
        json={
            "slug": "custom-vllm",
            "display_name": "Custom vLLM",
            "endpoint_url": "http://llm-alt:8000",
            "enabled": True,
            "config": {"request_format": "openai_chat"},
            "secret_refs": {"api_key": "env://VLLM_API_KEY"},
        },
    )
    delete_provider_response = test_client.delete("/v1/platform/providers/provider-2", headers=_auth(token))
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
    update_deployment_response = test_client.put(
        "/v1/platform/deployments/deployment-2",
        headers=_auth(token),
        json={
            "slug": "staging-profile",
            "display_name": "Staging Profile",
            "bindings": [],
        },
    )
    clone_deployment_response = test_client.post(
        "/v1/platform/deployments/deployment-1/clone",
        headers=_auth(token),
        json={
            "slug": "cloned-profile",
            "display_name": "Cloned Profile",
        },
    )
    activate_response = test_client.post(
        "/v1/platform/deployments/deployment-2/activate",
        headers=_auth(token),
    )
    delete_deployment_response = test_client.delete("/v1/platform/deployments/deployment-3", headers=_auth(token))
    validate_response = test_client.post(
        "/v1/platform/providers/provider-1/validate",
        headers=_auth(token),
    )
    ensure_response = test_client.post(
        "/v1/platform/vector/indexes/ensure",
        headers=_auth(token),
        json={"index": "knowledge_base"},
    )
    upsert_response = test_client.post(
        "/v1/platform/vector/documents/upsert",
        headers=_auth(token),
        json={"index": "knowledge_base", "documents": [{"id": "doc-1", "text": "hello"}]},
    )
    query_response = test_client.post(
        "/v1/platform/vector/query",
        headers=_auth(token),
        json={"index": "knowledge_base", "query_text": "hello"},
    )
    delete_response = test_client.post(
        "/v1/platform/vector/documents/delete",
        headers=_auth(token),
        json={"index": "knowledge_base", "ids": ["doc-1"]},
    )

    assert providers.status_code == 200
    assert providers.get_json()["providers"][0]["slug"] == "vllm-local-gateway"
    assert provider_families.status_code == 200
    assert provider_families.get_json()["provider_families"][0]["provider_key"] == "vllm_local"
    assert activation_audit.status_code == 200
    assert activation_audit.get_json()["activation_audit"][0]["deployment_profile"]["slug"] == "local-default"
    assert create_provider_response.status_code == 201
    assert create_provider_response.get_json()["provider"]["secret_refs"]["api_key"] == "env://VLLM_API_KEY"
    assert update_provider_response.status_code == 200
    assert update_provider_response.get_json()["provider"]["config"]["request_format"] == "openai_chat"
    assert delete_provider_response.status_code == 200
    assert delete_provider_response.get_json()["deleted"] is True
    assert deployments.status_code == 200
    assert deployments.get_json()["deployments"][0]["is_active"] is True
    assert create_response.status_code == 201
    assert create_response.get_json()["deployment_profile"]["slug"] == "staging-profile"
    assert update_deployment_response.status_code == 200
    assert update_deployment_response.get_json()["deployment_profile"]["slug"] == "staging-profile"
    assert clone_deployment_response.status_code == 201
    assert clone_deployment_response.get_json()["deployment_profile"]["slug"] == "cloned-profile"
    assert activate_response.status_code == 200
    assert activate_response.get_json()["deployment_profile"]["is_active"] is True
    assert delete_deployment_response.status_code == 200
    assert delete_deployment_response.get_json()["deleted"] is True
    assert validate_response.status_code == 200
    assert validate_response.get_json()["validation"]["health"]["reachable"] is True
    assert ensure_response.status_code == 200
    assert ensure_response.get_json()["index"]["name"] == "knowledge_base"
    assert upsert_response.status_code == 200
    assert upsert_response.get_json()["documents"][0]["status"] == "upserted"
    assert query_response.status_code == 200
    assert query_response.get_json()["results"][0]["id"] == "doc-1"
    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted_ids"] == ["doc-1"]


def test_platform_vector_routes_return_control_plane_errors(client, monkeypatch: pytest.MonkeyPatch):
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
        "query_vector_documents",
        lambda _db, _config, payload: (_ for _ in ()).throw(
            PlatformControlPlaneError("invalid_query_input", "Provide exactly one of query_text or embedding", status_code=400)
        ),
    )

    response = test_client.post(
        "/v1/platform/vector/query",
        headers=_auth(token),
        json={"index": "knowledge_base", "query_text": "hello", "embedding": [0.1]},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_query_input",
        "message": "Provide exactly one of query_text or embedding",
    }


def test_activate_route_returns_preflight_validation_errors(client, monkeypatch: pytest.MonkeyPatch):
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
        "activate_deployment_profile",
        lambda _db, *, config, deployment_profile_id, activated_by_user_id: (_ for _ in ()).throw(
            PlatformControlPlaneError(
                "deployment_profile_validation_failed",
                "Deployment profile preflight validation failed",
                status_code=409,
                details={"providers": [{"provider": {"slug": "broken-provider"}}]},
            )
        ),
    )

    response = test_client.post("/v1/platform/deployments/deployment-2/activate", headers=_auth(token))

    assert response.status_code == 409
    assert response.get_json()["error"] == "deployment_profile_validation_failed"
    assert response.get_json()["details"]["providers"][0]["provider"]["slug"] == "broken-provider"
