from __future__ import annotations

from app.application import agent_projects_service


def _project_row() -> dict[str, object]:
    return {
        "id": "proj-1",
        "owner_user_id": 10,
        "published_agent_id": None,
        "current_version": 1,
        "visibility": "private",
        "created_at": "2026-03-18T11:00:00+00:00",
        "updated_at": "2026-03-18T11:00:00+00:00",
        "name": "Support Agent",
        "description": "Handles support workflows.",
        "instructions": "Be helpful.",
        "default_model_ref": "safe-small",
        "tool_refs": ["tool.web_search"],
        "workflow_definition": {"entrypoint": "assistant"},
        "tool_policy": {"allow_user_tools": False},
        "runtime_constraints": {"internet_required": False, "sandbox_required": False},
    }


def test_validate_agent_project_reports_runtime_constraint_mismatches(monkeypatch):
    monkeypatch.setattr(agent_projects_service, "get_agent_project", lambda *_args, **_kwargs: _project_row())
    monkeypatch.setattr(agent_projects_service, "find_model_definition", lambda *_args, **_kwargs: {"id": "safe-small"})
    monkeypatch.setattr(
        agent_projects_service,
        "find_registry_entity",
        lambda *_args, **_kwargs: {
            "entity_id": "tool.web_search",
            "current_spec": {
                "name": "Web search",
                "tool_name": "web_search",
                "transport": "mcp",
                "offline_compatible": False,
            },
        },
    )

    payload = agent_projects_service.validate_agent_project(
        "postgresql://ignored",
        project_id="proj-1",
        actor_user_id=10,
        actor_role="user",
    )

    assert payload["validation"]["valid"] is False
    assert payload["validation"]["derived_runtime_requirements"]["internet_required"] is True
    assert payload["validation"]["errors"] == [
        "Project references online-only tools but runtime_constraints.internet_required is false.",
    ]


def test_publish_agent_project_compiles_catalog_payload_and_persists_published_agent_id(monkeypatch):
    create_calls: list[dict[str, object]] = []

    monkeypatch.setattr(agent_projects_service, "get_agent_project", lambda *_args, **_kwargs: _project_row())
    monkeypatch.setattr(agent_projects_service, "find_registry_entity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        agent_projects_service,
        "create_catalog_agent",
        lambda _database_url, *, payload, owner_user_id: create_calls.append({"payload": payload, "owner_user_id": owner_user_id}) or {"id": payload["id"], "name": payload["name"]},
    )
    monkeypatch.setattr(
        agent_projects_service,
        "set_published_agent_id",
        lambda *_args, **_kwargs: {**_project_row(), "published_agent_id": "agent.project.proj-1"},
    )

    payload = agent_projects_service.publish_agent_project(
        "postgresql://ignored",
        project_id="proj-1",
        actor_user_id=10,
        actor_role="user",
    )

    assert create_calls[0]["owner_user_id"] == 10
    assert create_calls[0]["payload"]["tool_refs"] == ["tool.web_search"]
    assert payload["publish_result"]["agent_id"] == "agent.project.proj-1"


def test_build_agent_project_preview_returns_previewable_runtime_shape(monkeypatch):
    monkeypatch.setattr(agent_projects_service, "get_agent_project", lambda *_args, **_kwargs: _project_row())

    payload = agent_projects_service.build_agent_project_preview(
        "postgresql://ignored",
        project_id="proj-1",
        actor_user_id=10,
        actor_role="user",
    )

    assert payload == {
        "project_id": "proj-1",
        "assistant_ref": "agent.project.proj-1",
        "playground_kind": "chat",
        "default_model_ref": "safe-small",
        "tool_refs": ["tool.web_search"],
        "runtime_constraints": {"internet_required": False, "sandbox_required": False},
        "workflow_definition": {"entrypoint": "assistant"},
    }
