from __future__ import annotations

import pytest

from app.routes import executions as executions_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.agent_engine_client import AgentEngineClientError  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(executions_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(executions_routes, "_config", lambda: config)
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_agent_execution_success_proxy(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u3@example.com",
        username="u3",
        password_hash=hash_password("u3-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u3-pass-123").get_json()["access_token"]
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
                "embeddings": {
                    "id": "provider-embeddings",
                    "slug": "vllm-embeddings-local",
                    "provider_key": "vllm_embeddings_local",
                    "display_name": "vLLM embeddings local",
                    "description": "desc",
                    "adapter_kind": "openai_compatible_embeddings",
                    "endpoint_url": "http://llm:8000",
                    "healthcheck_url": "http://llm:8000/health",
                    "enabled": True,
                    "config": {"embeddings_path": "/v1/embeddings", "forced_model_id": "local-vllm-embeddings-default"},
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

    def _create_execution(**kwargs):
        assert kwargs["agent_id"] == "agent.local"
        assert kwargs["runtime_profile"] == "offline"
        assert kwargs["requested_by_user_id"] == user["id"]
        assert kwargs["execution_input"]["retrieval"] == {
            "index": "knowledge_base",
            "top_k": 3,
            "filters": {"tenant": "ops"},
        }
        assert kwargs["platform_runtime"]["deployment_profile"]["slug"] == "local-default"
        assert kwargs["platform_runtime"]["capabilities"]["llm_inference"]["provider_key"] == "vllm_local"
        assert kwargs["platform_runtime"]["capabilities"]["embeddings"]["provider_key"] == "vllm_embeddings_local"
        assert kwargs["platform_runtime"]["capabilities"]["vector_store"]["provider_key"] == "weaviate_local"
        return (
            {
                "execution": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": "agent.local",
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
            201,
        )

    monkeypatch.setattr(executions_routes, "create_execution", _create_execution)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={
            "agent_id": "agent.local",
            "input": {
                "prompt": "hello",
                "retrieval": {
                    "index": "knowledge_base",
                    "top_k": 3,
                    "filters": {"tenant": "ops"},
                },
            },
        },
    )
    assert response.status_code == 201
    payload = response.get_json()["execution"]
    assert payload["id"] == "exec-1"
    assert payload["runtime_profile"] == "offline"


def test_agent_execution_proxy_forwards_qdrant_runtime_snapshot(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u11@example.com",
        username="u11",
        password_hash=hash_password("u11-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u11-pass-123").get_json()["access_token"]
    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: {
            "deployment_profile": {"id": "dep-2", "slug": "local-qdrant", "display_name": "Local Qdrant"},
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
                "embeddings": {
                    "id": "provider-embeddings",
                    "slug": "vllm-embeddings-local",
                    "provider_key": "vllm_embeddings_local",
                    "display_name": "vLLM embeddings local",
                    "description": "desc",
                    "adapter_kind": "openai_compatible_embeddings",
                    "endpoint_url": "http://llm:8000",
                    "healthcheck_url": "http://llm:8000/health",
                    "enabled": True,
                    "config": {"embeddings_path": "/v1/embeddings", "forced_model_id": "local-vllm-embeddings-default"},
                    "binding_config": {},
                },
                "vector_store": {
                    "id": "provider-3",
                    "slug": "qdrant-local",
                    "provider_key": "qdrant_local",
                    "display_name": "Qdrant local",
                    "description": "desc",
                    "adapter_kind": "qdrant_http",
                    "endpoint_url": "http://qdrant:6333",
                    "healthcheck_url": "http://qdrant:6333/healthz",
                    "enabled": True,
                    "config": {},
                    "binding_config": {},
                },
            },
        },
    )

    def _create_execution(**kwargs):
        assert kwargs["platform_runtime"]["deployment_profile"]["slug"] == "local-qdrant"
        assert kwargs["platform_runtime"]["capabilities"]["embeddings"]["provider_key"] == "vllm_embeddings_local"
        assert kwargs["platform_runtime"]["capabilities"]["vector_store"]["provider_key"] == "qdrant_local"
        assert kwargs["execution_input"]["retrieval"] == {"index": "knowledge_base"}
        return (
            {
                "execution": {
                    "id": "exec-qdrant",
                    "status": "succeeded",
                    "agent_ref": "agent.local",
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
            201,
        )

    monkeypatch.setattr(executions_routes, "create_execution", _create_execution)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {"prompt": "hello", "retrieval": {"index": "knowledge_base"}}},
    )

    assert response.status_code == 201
    assert response.get_json()["execution"]["id"] == "exec-qdrant"


def test_agent_execution_passes_engine_errors(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u2@example.com",
        username="u2",
        password_hash=hash_password("u2-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u2-pass-123").get_json()["access_token"]
    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: {"deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"}, "capabilities": {}},
    )

    def _create_execution(**_kwargs):
        raise AgentEngineClientError(
            code="EXEC_RUNTIME_PROFILE_BLOCKED",
            message="Blocked in offline profile",
            status_code=403,
        )

    monkeypatch.setattr(executions_routes, "create_execution", _create_execution)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.internet", "input": {}},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "EXEC_RUNTIME_PROFILE_BLOCKED"


def test_agent_execution_invalid_input(client):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u4@example.com",
        username="u4",
        password_hash=hash_password("u4-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u4-pass-123").get_json()["access_token"]

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": "bad"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_input"


def test_get_agent_execution_proxy(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u5@example.com",
        username="u5",
        password_hash=hash_password("u5-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u5-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        executions_routes,
        "get_execution",
        lambda **_kwargs: (
            {
                "execution": {
                    "id": "exec-5",
                    "status": "succeeded",
                    "agent_ref": "agent.local",
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
    response = test_client.get("/v1/agent-executions/exec-5", headers=_auth(token))
    assert response.status_code == 200
    assert response.get_json()["execution"]["id"] == "exec-5"


def test_fallback_enabled_create_unreachable_returns_deterministic_503(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u6@example.com",
        username="u6",
        password_hash=hash_password("u6-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u6-pass-123").get_json()["access_token"]

    monkeypatch.setattr(executions_routes, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(executions_routes, "_request_id", lambda: "req-create-fallback")
    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: {"deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"}, "capabilities": {}},
    )

    def _create_execution(**_kwargs):
        raise AgentEngineClientError(
            code="agent_engine_unreachable",
            message="Agent engine unavailable",
            status_code=502,
        )

    monkeypatch.setattr(executions_routes, "create_execution", _create_execution)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {"prompt": "hello"}},
    )
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["error"] == "EXEC_UPSTREAM_UNAVAILABLE"
    assert payload["details"]["fallback_applied"] is True
    assert payload["details"]["operation"] == "create_execution"
    assert payload["details"]["request_id"] == "req-create-fallback"


def test_fallback_enabled_get_timeout_returns_deterministic_503(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u7@example.com",
        username="u7",
        password_hash=hash_password("u7-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u7-pass-123").get_json()["access_token"]

    monkeypatch.setattr(executions_routes, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(executions_routes, "_request_id", lambda: "req-get-fallback")
    monkeypatch.setattr(
        executions_routes,
        "get_execution",
        lambda **_kwargs: (_ for _ in ()).throw(
            AgentEngineClientError(
                code="EXEC_TIMEOUT",
                message="timeout",
                status_code=504,
            )
        ),
    )

    response = test_client.get("/v1/agent-executions/exec-timeout", headers=_auth(token))
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["error"] == "EXEC_UPSTREAM_UNAVAILABLE"
    assert payload["details"]["fallback_applied"] is True
    assert payload["details"]["operation"] == "get_execution"
    assert payload["details"]["request_id"] == "req-get-fallback"


def test_fallback_enabled_does_not_mask_403_policy_denial(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u8@example.com",
        username="u8",
        password_hash=hash_password("u8-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u8-pass-123").get_json()["access_token"]

    monkeypatch.setattr(executions_routes, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: {"deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"}, "capabilities": {}},
    )
    monkeypatch.setattr(
        executions_routes,
        "create_execution",
        lambda **_kwargs: (_ for _ in ()).throw(
            AgentEngineClientError(
                code="EXEC_POLICY_DENIED",
                message="Denied",
                status_code=403,
            )
        ),
    )

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {}},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "EXEC_POLICY_DENIED"


def test_fallback_disabled_preserves_upstream_unreachable_mapping(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u9@example.com",
        username="u9",
        password_hash=hash_password("u9-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u9-pass-123").get_json()["access_token"]

    monkeypatch.setattr(executions_routes, "_fallback_enabled", lambda: False)
    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: {"deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"}, "capabilities": {}},
    )
    monkeypatch.setattr(
        executions_routes,
        "create_execution",
        lambda **_kwargs: (_ for _ in ()).throw(
            AgentEngineClientError(
                code="agent_engine_unreachable",
                message="Agent engine unavailable",
                status_code=502,
            )
        ),
    )

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {}},
    )
    assert response.status_code == 502
    payload = response.get_json()
    assert payload["error"] == "agent_engine_unreachable"


def test_agent_execution_returns_platform_control_plane_error(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u10@example.com",
        username="u10",
        password_hash=hash_password("u10-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u10-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        executions_routes,
        "get_active_platform_runtime",
        lambda _db, _config: (_ for _ in ()).throw(
            PlatformControlPlaneError(
                "active_binding_not_found",
                "No active provider binding for capability 'llm_inference'",
                status_code=503,
            )
        ),
    )

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {"prompt": "hello"}},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "active_binding_not_found"
