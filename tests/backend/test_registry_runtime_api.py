from __future__ import annotations

from typing import Any

import pytest

from app.routes import executions as executions_routes  # noqa: E402
from app.routes import registry as registry_routes  # noqa: E402
from app.routes import registry_models as registry_models_routes  # noqa: E402
from app.routes import runtime as runtime_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import runtime_profile_service  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()

    registry_items: dict[str, dict[str, Any]] = {}
    shares_by_entity: dict[str, list[dict[str, Any]]] = {}

    monkeypatch.setattr(registry_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(registry_models_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(runtime_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(executions_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(executions_routes, "_config", lambda: config)

    def _create_entity_with_version(
        _database_url: str,
        *,
        entity_type: str,
        entity_id: str,
        owner_user_id: int,
        visibility: str,
        spec: dict[str, Any],
        version: str,
        publish: bool,
    ) -> dict[str, Any]:
        item = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "owner_user_id": owner_user_id,
            "visibility": visibility,
            "status": "published" if publish else "draft",
            "current_version": version,
            "current_spec": spec,
        }
        registry_items[f"{entity_type}:{entity_id}"] = item
        return {
            "entity": item,
            "version": {"entity_id": entity_id, "version": version, "spec_json": spec},
        }

    def _list_entities(_database_url: str, *, entity_type: str) -> list[dict[str, Any]]:
        return [item for item in registry_items.values() if item["entity_type"] == entity_type]

    def _get_entity(_database_url: str, *, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        return registry_items.get(f"{entity_type}:{entity_id}")

    def _get_entity_versions(_database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
        for item in registry_items.values():
            if item["entity_id"] == entity_id:
                return [{"entity_id": entity_id, "version": item["current_version"], "spec_json": item["current_spec"]}]
        return []

    def _create_entity_version(
        _database_url: str,
        *,
        entity_type: str,
        entity_id: str,
        version: str,
        spec: dict[str, Any],
        publish: bool,
    ) -> dict[str, Any]:
        item = registry_items[f"{entity_type}:{entity_id}"]
        item["current_version"] = version
        item["current_spec"] = spec
        item["status"] = "published" if publish else "draft"
        return {
            "entity": item,
            "version": {"entity_id": entity_id, "version": version, "spec_json": spec},
        }

    def _grant_share(
        _database_url: str,
        *,
        current_user: dict[str, Any],
        entity: dict[str, Any],
        grantee_type: str,
        grantee_id: str | None,
        permission: str,
    ) -> dict[str, Any]:
        share = {
            "entity_id": entity["entity_id"],
            "grantee_type": grantee_type,
            "grantee_id": grantee_id,
            "permission": permission,
            "shared_by_user_id": current_user["id"],
        }
        shares_by_entity.setdefault(entity["entity_id"], []).append(share)
        return share

    monkeypatch.setattr(registry_routes, "create_entity_with_version", _create_entity_with_version)
    monkeypatch.setattr(registry_models_routes, "create_entity_with_version", _create_entity_with_version)
    monkeypatch.setattr(registry_routes, "list_entities", _list_entities)
    monkeypatch.setattr(registry_models_routes, "list_entities", _list_entities)
    monkeypatch.setattr(registry_routes, "get_entity", _get_entity)
    monkeypatch.setattr(registry_models_routes, "get_entity", _get_entity)
    monkeypatch.setattr(registry_routes, "get_entity_versions", _get_entity_versions)
    monkeypatch.setattr(registry_models_routes, "get_entity_versions", _get_entity_versions)
    monkeypatch.setattr(registry_routes, "create_entity_version", _create_entity_version)
    monkeypatch.setattr(registry_models_routes, "create_entity_version", _create_entity_version)
    monkeypatch.setattr(registry_routes, "grant_share", _grant_share)
    monkeypatch.setattr(registry_models_routes, "grant_share", _grant_share)
    monkeypatch.setattr(registry_routes, "get_shares", lambda _db, *, entity_id: shares_by_entity.get(entity_id, []))
    monkeypatch.setattr(registry_models_routes, "get_shares", lambda _db, *, entity_id: shares_by_entity.get(entity_id, []))

    monkeypatch.setattr(runtime_routes, "resolve_runtime_profile", lambda _db: "offline")
    monkeypatch.setattr(runtime_routes, "update_runtime_profile", lambda _db, *, profile, updated_by_user_id: profile)

    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_registry_and_runtime_endpoints(client):
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

    create_response = test_client.post(
        "/v1/registry/agents",
        headers=_auth(token),
        json={
            "id": "agent.alpha",
            "version": "v1",
            "visibility": "private",
            "publish": False,
            "spec": {
                "name": "Agent Alpha",
                "description": "test agent",
                "instructions": "be concise",
                "default_model_ref": "model.default",
                "tool_refs": [],
                "runtime_constraints": {"internet_required": False, "sandbox_required": True},
            },
        },
    )
    assert create_response.status_code == 201

    list_response = test_client.get("/v1/registry/agents", headers=_auth(token))
    assert list_response.status_code == 200
    assert list_response.get_json()["items"][0]["entity_id"] == "agent.alpha"

    share_response = test_client.post(
        "/v1/registry/agents/agent.alpha/share",
        headers=_auth(token),
        json={"grantee_type": "public", "permission": "view"},
    )
    assert share_response.status_code == 201

    runtime_get = test_client.get("/v1/runtime/profile", headers=_auth(token))
    assert runtime_get.status_code == 200
    assert runtime_get.get_json()["profile"] == "offline"

    runtime_set = test_client.put(
        "/v1/runtime/profile",
        headers=_auth(token),
        json={"profile": "air_gapped"},
    )
    assert runtime_set.status_code == 200
    assert runtime_set.get_json()["profile"] == "air_gapped"


def test_runtime_profile_read_requires_auth(client):
    test_client, _ = client

    response = test_client.get("/v1/runtime/profile")

    assert response.status_code == 401


def test_runtime_profile_write_rejects_non_superadmin(client):
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

    response = test_client.put(
        "/v1/runtime/profile",
        headers=_auth(token),
        json={"profile": "air_gapped"},
    )

    assert response.status_code == 403


def test_agent_execution_proxy_endpoints(client, monkeypatch: pytest.MonkeyPatch):
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
        executions_routes,
        "create_execution",
        lambda **kwargs: (
            {
                "execution": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": kwargs["agent_id"],
                    "agent_version": "v1",
                    "model_ref": None,
                    "runtime_profile": kwargs["runtime_profile"],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "result": {"output_text": "ok"},
                    "error": None,
                }
            },
            201,
        ),
    )
    monkeypatch.setattr(
        executions_routes,
        "get_execution",
        lambda **_kwargs: (
            {
                "execution": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": "agent.alpha",
                    "agent_version": "v1",
                    "model_ref": None,
                    "runtime_profile": "offline",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "result": {"output_text": "ok"},
                    "error": None,
                }
            },
            200,
        ),
    )
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")
    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: {
            "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
            "capabilities": {
                "llm_inference": {
                    "id": "provider-1",
                    "slug": "vllm-local-gateway",
                    "provider_key": "vllm_local",
                    "display_name": "vLLM local gateway",
                    "description": "desc",
                    "adapter_kind": "openai_compatible_llm",
                    "endpoint_url": "http://llm:8000",
                    "healthcheck_url": "http://llm:8000/health",
                    "enabled": True,
                    "config": {"chat_completion_path": "/v1/chat/completions"},
                    "binding_config": {},
                },
                "vector_store": {
                    "id": "provider-2",
                    "slug": "weaviate-local",
                    "provider_key": "weaviate_local",
                    "display_name": "Weaviate local",
                    "description": "desc",
                    "adapter_kind": "weaviate_http",
                    "endpoint_url": "http://weaviate:8080",
                    "healthcheck_url": "http://weaviate:8080/v1/.well-known/ready",
                    "enabled": True,
                    "config": {},
                    "binding_config": {},
                },
            },
        },
    )

    create_response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.alpha", "input": {"prompt": "hi"}},
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["execution"]["id"] == "exec-1"

    get_response = test_client.get("/v1/agent-executions/exec-1", headers=_auth(token))
    assert get_response.status_code == 200
    assert get_response.get_json()["execution"]["status"] == "succeeded"


def test_runtime_profile_resolution_prefers_db_when_no_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        runtime_profile_service,
        "get_backend_runtime_config",
        lambda: type("Config", (), {"runtime_profile_override": None})(),
    )
    monkeypatch.setattr(runtime_profile_service, "get_runtime_profile", lambda _db: "air_gapped")

    assert runtime_profile_service.resolve_runtime_profile("ignored") == "air_gapped"


def test_runtime_profile_resolution_uses_default_when_db_invalid_and_no_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        runtime_profile_service,
        "get_backend_runtime_config",
        lambda: type("Config", (), {"runtime_profile_override": None})(),
    )
    monkeypatch.setattr(runtime_profile_service, "get_runtime_profile", lambda _db: "invalid")

    assert runtime_profile_service.resolve_runtime_profile("ignored") == "offline"
