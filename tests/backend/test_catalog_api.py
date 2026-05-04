from __future__ import annotations

import pytest

from app.api.http import catalog as catalog_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(catalog_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(catalog_routes, "_config", lambda: config)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _root_user(user_store):
    return user_store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )


def test_catalog_routes_require_superadmin(client):
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

    responses = [
        test_client.get("/v1/catalog/defaults", headers=_auth(token)),
        test_client.get("/v1/catalog/agents", headers=_auth(token)),
        test_client.post("/v1/catalog/agents", headers=_auth(token), json={}),
        test_client.post("/v1/catalog/agents/prompt-preview", headers=_auth(token), json={}),
        test_client.get("/v1/catalog/agents/agent.alpha", headers=_auth(token)),
        test_client.get("/v1/catalog/agents/agent.alpha/prompt-preview", headers=_auth(token)),
        test_client.put("/v1/catalog/agents/agent.alpha", headers=_auth(token), json={}),
        test_client.post("/v1/catalog/agents/agent.alpha/validate", headers=_auth(token)),
        test_client.get("/v1/catalog/tools", headers=_auth(token)),
        test_client.post("/v1/catalog/tools", headers=_auth(token), json={}),
        test_client.get("/v1/catalog/tools/tool.alpha", headers=_auth(token)),
        test_client.put("/v1/catalog/tools/tool.alpha", headers=_auth(token), json={}),
        test_client.post("/v1/catalog/tools/tool.alpha/validate", headers=_auth(token)),
        test_client.post("/v1/catalog/tools/tool.alpha/test", headers=_auth(token), json={}),
    ]

    for response in responses:
        assert response.status_code == 403


def test_superadmin_catalog_routes_work(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    root = _root_user(user_store)
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]

    agent_row = {
        "id": "agent.alpha",
        "entity": {"id": "agent.alpha", "type": "agent", "owner_user_id": root["id"], "visibility": "private"},
        "current_version": "v1",
        "status": "draft",
        "published": False,
        "published_at": None,
        "spec": {
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "default_model_ref": "safe-small",
            "tool_refs": ["tool.web_search"],
            "runtime_constraints": {"internet_required": True, "sandbox_required": False},
        },
    }
    tool_row = {
        "id": "tool.web_search",
        "entity": {"id": "tool.web_search", "type": "tool", "owner_user_id": root["id"], "visibility": "private"},
        "current_version": "v1",
        "status": "published",
        "published": True,
        "published_at": "2026-01-01T00:00:00+00:00",
        "spec": {
            "name": "Web search",
            "description": "desc",
            "transport": "mcp",
            "connection_profile_ref": "default",
            "tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
        },
    }

    monkeypatch.setattr(catalog_routes, "list_catalog_agents", lambda _db: [agent_row])
    monkeypatch.setattr(
        catalog_routes,
        "get_catalog_defaults",
        lambda: {"agent": {"runtime_prompts": {"retrieval_context": "Default retrieval instructions."}}},
    )
    monkeypatch.setattr(catalog_routes, "get_catalog_agent", lambda _db, *, agent_id: dict(agent_row, id=agent_id))
    monkeypatch.setattr(catalog_routes, "create_catalog_agent", lambda _db, *, payload, owner_user_id: dict(agent_row, id=payload["id"]))
    monkeypatch.setattr(catalog_routes, "update_catalog_agent", lambda _db, *, agent_id, payload: dict(agent_row, id=agent_id, published=payload["publish"]))
    monkeypatch.setattr(
        catalog_routes,
        "preview_catalog_agent_prompt_payload",
        lambda payload: {"prompt_preview": {"messages": [], "text": f"draft:{payload['instructions']}"}},
    )
    monkeypatch.setattr(
        catalog_routes,
        "preview_catalog_agent_prompt",
        lambda _db, *, agent_id: {"agent": dict(agent_row, id=agent_id), "prompt_preview": {"messages": [], "text": f"stored:{agent_id}"}},
    )
    deleted_agents: list[dict[str, object]] = []
    monkeypatch.setattr(
        catalog_routes,
        "delete_catalog_agent",
        lambda _db, *, agent_id, actor_user_id, actor_role: deleted_agents.append(
            {"agent_id": agent_id, "actor_user_id": actor_user_id, "actor_role": actor_role}
        ),
    )
    monkeypatch.setattr(
        catalog_routes,
        "validate_catalog_agent",
        lambda _db, *, agent_id: {
            "agent": dict(agent_row, id=agent_id),
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": [],
                "resolved_tools": [{"id": "tool.web_search", "name": "Web search", "transport": "mcp", "offline_compatible": False}],
                "derived_runtime_requirements": {"internet_required": True, "sandbox_required": False},
            },
        },
    )

    monkeypatch.setattr(catalog_routes, "list_catalog_tools", lambda _db: [tool_row])
    monkeypatch.setattr(catalog_routes, "get_catalog_tool", lambda _db, *, tool_id: dict(tool_row, id=tool_id))
    monkeypatch.setattr(catalog_routes, "create_catalog_tool", lambda _db, *, payload, owner_user_id: dict(tool_row, id=payload["id"]))
    monkeypatch.setattr(catalog_routes, "update_catalog_tool", lambda _db, *, tool_id, payload: dict(tool_row, id=tool_id, published=payload["publish"]))
    monkeypatch.setattr(
        catalog_routes,
        "validate_catalog_tool",
        lambda _db, *, config, tool_id: {
            "tool": dict(tool_row, id=tool_id),
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": [],
                "runtime_checks": {"runtime_capability": "mcp_runtime", "tool_discovered": True},
            },
        },
    )
    monkeypatch.setattr(
        catalog_routes,
        "execute_catalog_tool",
        lambda _db, *, config, tool_id, payload, actor_user_id: {
            "tool": dict(tool_row, id=tool_id),
            "execution": {
                "input": payload["input"],
                "request_metadata": {"actor_user_id": actor_user_id},
                "status_code": 200,
                "ok": True,
                "result": {"results": [{"title": "Example"}]},
            },
        },
    )

    defaults = test_client.get("/v1/catalog/defaults", headers=_auth(token))
    agents = test_client.get("/v1/catalog/agents", headers=_auth(token))
    create_agent = test_client.post(
        "/v1/catalog/agents",
        headers=_auth(token),
        json={
            "id": "agent.alpha",
            "publish": False,
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "default_model_ref": "safe-small",
            "tool_refs": ["tool.web_search"],
            "runtime_constraints": {"internet_required": True, "sandbox_required": False},
        },
    )
    update_agent = test_client.put(
        "/v1/catalog/agents/agent.alpha",
        headers=_auth(token),
        json={
            "publish": True,
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "default_model_ref": "safe-small",
            "tool_refs": ["tool.web_search"],
            "runtime_constraints": {"internet_required": True, "sandbox_required": False},
        },
    )
    validate_agent = test_client.post("/v1/catalog/agents/agent.alpha/validate", headers=_auth(token))
    draft_prompt_preview = test_client.post(
        "/v1/catalog/agents/prompt-preview",
        headers=_auth(token),
        json={
            "instructions": "draft instructions",
            "runtime_prompts": {"retrieval_context": "draft retrieval"},
        },
    )
    stored_prompt_preview = test_client.get("/v1/catalog/agents/agent.alpha/prompt-preview", headers=_auth(token))
    delete_agent = test_client.delete("/v1/catalog/agents/agent.alpha", headers=_auth(token))

    tools = test_client.get("/v1/catalog/tools", headers=_auth(token))
    create_tool = test_client.post(
        "/v1/catalog/tools",
        headers=_auth(token),
        json={
            "id": "tool.web_search",
            "publish": True,
            "name": "Web search",
            "description": "desc",
            "transport": "mcp",
            "connection_profile_ref": "default",
            "tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
        },
    )
    update_tool = test_client.put(
        "/v1/catalog/tools/tool.web_search",
        headers=_auth(token),
        json={
            "publish": False,
            "name": "Web search",
            "description": "desc",
            "transport": "mcp",
            "connection_profile_ref": "default",
            "tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
        },
    )
    validate_tool = test_client.post("/v1/catalog/tools/tool.web_search/validate", headers=_auth(token))
    execute_tool = test_client.post(
        "/v1/catalog/tools/tool.web_search/test",
        headers=_auth(token),
        json={"input": {"query": "OpenAI"}},
    )

    assert defaults.status_code == 200
    assert defaults.get_json()["defaults"]["agent"]["runtime_prompts"]["retrieval_context"] == "Default retrieval instructions."
    assert agents.status_code == 200
    assert agents.get_json()["agents"][0]["id"] == "agent.alpha"
    assert create_agent.status_code == 201
    assert update_agent.status_code == 200
    assert update_agent.get_json()["agent"]["published"] is True
    assert validate_agent.status_code == 200
    assert validate_agent.get_json()["validation"]["valid"] is True
    assert draft_prompt_preview.status_code == 200
    assert draft_prompt_preview.get_json()["prompt_preview"]["text"] == "draft:draft instructions"
    assert stored_prompt_preview.status_code == 200
    assert stored_prompt_preview.get_json()["prompt_preview"]["text"] == "stored:agent.alpha"
    assert delete_agent.status_code == 200
    assert delete_agent.get_json()["deleted"] is True
    assert deleted_agents == [{"agent_id": "agent.alpha", "actor_user_id": root["id"], "actor_role": "superadmin"}]

    assert tools.status_code == 200
    assert tools.get_json()["tools"][0]["id"] == "tool.web_search"
    assert create_tool.status_code == 201
    assert update_tool.status_code == 200
    assert update_tool.get_json()["tool"]["published"] is False
    assert validate_tool.status_code == 200
    assert validate_tool.get_json()["validation"]["runtime_checks"]["tool_discovered"] is True
    assert execute_tool.status_code == 200
    assert execute_tool.get_json()["execution"]["ok"] is True
    assert execute_tool.get_json()["execution"]["result"]["results"][0]["title"] == "Example"
