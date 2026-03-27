from __future__ import annotations

import pytest

from app.api.http import agent_projects as agent_project_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, _config = backend_test_client_factory()
    monkeypatch.setattr(agent_project_routes, "_database_url", lambda: "ignored")
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _project(project_id: str = "proj-1") -> dict[str, object]:
    return {
        "id": project_id,
        "owner_user_id": 10,
        "published_agent_id": None,
        "current_version": 1,
        "visibility": "private",
        "created_at": "2026-03-18T11:00:00+00:00",
        "updated_at": "2026-03-18T11:00:00+00:00",
        "spec": {
            "name": "Support Agent",
            "description": "Handles support workflows.",
            "instructions": "Be helpful.",
            "default_model_ref": "safe-small",
            "tool_refs": ["tool.web_search"],
            "workflow_definition": {"entrypoint": "assistant"},
            "tool_policy": {"allow_user_tools": False},
            "runtime_constraints": {"internet_required": True, "sandbox_required": False},
        },
    }


def test_agent_projects_routes_require_auth(client):
    test_client, _users = client

    response = test_client.get("/v1/agent-projects")

    assert response.status_code == 401


def test_create_agent_project_route_returns_service_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="builder@example.com",
        username="builder",
        password_hash=hash_password("builder-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "builder-pass-123").get_json()["access_token"]

    monkeypatch.setattr(agent_project_routes, "create_agent_project", lambda *_args, **_kwargs: _project("proj-new"))

    response = test_client.post(
        "/v1/agent-projects",
        headers=_auth(token),
        json={
            "id": "proj-new",
            "name": "Support Agent",
            "description": "Handles support workflows.",
            "instructions": "Be helpful.",
            "default_model_ref": "safe-small",
            "tool_refs": ["tool.web_search"],
            "workflow_definition": {"entrypoint": "assistant"},
            "tool_policy": {"allow_user_tools": False},
            "runtime_constraints": {"internet_required": True, "sandbox_required": False},
        },
    )

    assert response.status_code == 201
    assert response.get_json()["agent_project"]["id"] == "proj-new"


def test_get_agent_project_route_returns_not_found(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="missing-project@example.com",
        username="missing-project",
        password_hash=hash_password("missing-project-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "missing-project-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        agent_project_routes,
        "get_agent_project_detail",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            agent_project_routes.AgentProjectError("project_not_found", "Agent project not found", status_code=404),
        ),
    )

    response = test_client.get("/v1/agent-projects/missing", headers=_auth(token))

    assert response.status_code == 404
    assert response.get_json()["error"] == "project_not_found"


def test_validate_agent_project_route_returns_validation_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="validate@example.com",
        username="validator",
        password_hash=hash_password("validator-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "validator-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        agent_project_routes,
        "validate_agent_project",
        lambda *_args, **_kwargs: {
            "agent_project": _project(),
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": [],
                "resolved_tools": [],
                "derived_runtime_requirements": {"internet_required": True, "sandbox_required": False},
            },
        },
    )

    response = test_client.post("/v1/agent-projects/proj-1/validate", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["validation"]["valid"] is True


def test_publish_agent_project_route_returns_publish_result(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="publish@example.com",
        username="publisher",
        password_hash=hash_password("publisher-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "publisher-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        agent_project_routes,
        "publish_agent_project",
        lambda *_args, **_kwargs: {
            "agent_project": {**_project(), "published_agent_id": "agent.project.proj-1"},
            "publish_result": {
                "agent_id": "agent.project.proj-1",
                "catalog_agent": {"id": "agent.project.proj-1", "name": "Support Agent"},
                "published_at": "2026-03-18T11:00:02Z",
            },
        },
    )

    response = test_client.post("/v1/agent-projects/proj-1/publish", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["publish_result"]["agent_id"] == "agent.project.proj-1"
