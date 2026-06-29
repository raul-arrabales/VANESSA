from __future__ import annotations

from app.repositories import agent_projects as agent_projects_repo


class _FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.rowcount = 1

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        self.executions.append((query, params))


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return self._cursor


def test_create_agent_project_insert_query_matches_parameter_count(monkeypatch):
    cursor = _FakeCursor()
    spec = {
        "name": "Workflow Agent",
        "description": "desc",
        "instructions": "",
        "runtime_prompts": {"retrieval_context": ""},
        "default_model_ref": None,
        "tool_refs": [],
        "mcp_server_refs": ["web_search"],
        "agent_domain": "default",
        "agent_type": "workflow",
        "channel_type": "vanessa_webapp",
        "interface_type": "chat",
        "workflow_definition": {"version": 2, "actions": []},
        "tool_policy": {"allow_user_tools": False},
        "runtime_constraints": {"internet_required": False, "sandbox_required": False},
    }

    monkeypatch.setattr(agent_projects_repo, "get_connection", lambda _db: _FakeConnection(cursor))
    monkeypatch.setattr(
        agent_projects_repo,
        "get_agent_project",
        lambda _db, *, project_id: {
            "id": project_id,
            "owner_user_id": 1,
            "name": spec["name"],
            "description": spec["description"],
            "instructions": spec["instructions"],
            "runtime_prompts": spec["runtime_prompts"],
            "default_model_ref": spec["default_model_ref"],
            "tool_refs": spec["tool_refs"],
            "mcp_server_refs": spec["mcp_server_refs"],
            "agent_domain": spec["agent_domain"],
            "agent_type": spec["agent_type"],
            "channel_type": spec["channel_type"],
            "interface_type": spec["interface_type"],
            "workflow_definition": spec["workflow_definition"],
            "tool_policy": spec["tool_policy"],
            "runtime_constraints": spec["runtime_constraints"],
            "visibility": "private",
            "published_agent_id": None,
            "current_version": 1,
            "created_at": "2026-06-29T00:00:00+00:00",
            "updated_at": "2026-06-29T00:00:00+00:00",
        },
    )

    agent_projects_repo.create_agent_project(
        "ignored",
        project_id="workflow-agent-1",
        owner_user_id=1,
        spec=spec,
        visibility="private",
    )

    insert_query, insert_params = cursor.executions[0]
    assert "INSERT INTO agent_projects" in insert_query
    assert insert_query.count("%s") == len(insert_params)
