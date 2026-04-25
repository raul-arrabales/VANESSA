from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import catalog_service  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402


def test_create_and_update_catalog_agent_use_registry_versions(monkeypatch: pytest.MonkeyPatch):
    entities: dict[str, dict] = {}

    def _find_registry_entity(_db: str, *, entity_type: str, entity_id: str):
        return entities.get(f"{entity_type}:{entity_id}")

    def _create_registry_entity(_db: str, *, entity_id: str, entity_type: str, owner_user_id: int, visibility: str, status: str):
        row = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "owner_user_id": owner_user_id,
            "visibility": visibility,
            "status": status,
            "current_version": None,
            "current_spec": None,
            "published_at": None,
        }
        entities[f"{entity_type}:{entity_id}"] = row
        return row

    def _create_registry_version(_db: str, *, entity_id: str, version: str, spec_json: dict, set_current: bool, published: bool):
        row = entities[f"agent:{entity_id}"]
        row["current_version"] = version
        row["current_spec"] = spec_json
        row["published_at"] = "2026-01-01T00:00:00+00:00" if published else None
        return {"entity_id": entity_id, "version": version, "spec_json": spec_json}

    def _update_registry_entity(_db: str, *, entity_id: str, visibility: str | None = None, status: str | None = None):
        row = entities[f"agent:{entity_id}"]
        if visibility is not None:
            row["visibility"] = visibility
        if status is not None:
            row["status"] = status
        return row

    monkeypatch.setattr(catalog_service, "find_registry_entity", _find_registry_entity)
    monkeypatch.setattr(catalog_service, "create_registry_entity", _create_registry_entity)
    monkeypatch.setattr(catalog_service, "create_registry_version", _create_registry_version)
    monkeypatch.setattr(catalog_service, "update_registry_entity", _update_registry_entity)

    created = catalog_service.create_catalog_agent(
        "ignored",
        owner_user_id=3,
        payload={
            "id": "agent.alpha",
            "publish": False,
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "runtime_prompts": {"retrieval_context": "Use retrieved context."},
            "default_model_ref": None,
            "tool_refs": [],
            "runtime_constraints": {"internet_required": False, "sandbox_required": False},
        },
    )

    updated = catalog_service.update_catalog_agent(
        "ignored",
        agent_id="agent.alpha",
        payload={
            "publish": True,
            "name": "Agent Alpha",
            "description": "desc",
            "instructions": "be concise",
            "runtime_prompts": {"retrieval_context": "Use retrieved context and cite it."},
            "default_model_ref": "safe-small",
            "tool_refs": [],
            "runtime_constraints": {"internet_required": False, "sandbox_required": False},
        },
    )

    assert created["current_version"] == "v1"
    assert created["spec"]["runtime_prompts"]["retrieval_context"] == "Use retrieved context."
    assert created["published"] is False
    assert updated["current_version"] == "v2"
    assert updated["spec"]["runtime_prompts"]["retrieval_context"] == "Use retrieved context and cite it."
    assert updated["published"] is True
    assert updated["status"] == "published"


def test_delete_catalog_agent_blocks_platform_agent_and_allows_owner(monkeypatch: pytest.MonkeyPatch):
    rows = {
        "agent:agent.knowledge_chat": {
            "entity_id": "agent.knowledge_chat",
            "entity_type": "agent",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "current_spec": {},
            "published_at": "2026-01-01T00:00:00+00:00",
        },
        "agent:agent.user": {
            "entity_id": "agent.user",
            "entity_type": "agent",
            "owner_user_id": 7,
            "visibility": "private",
            "status": "draft",
            "current_version": "v1",
            "current_spec": {},
            "published_at": None,
        },
    }
    deleted: list[str] = []

    def _find_registry_entity(_db: str, *, entity_type: str, entity_id: str):
        return rows.get(f"{entity_type}:{entity_id}")

    def _delete_registry_entity(_db: str, *, entity_type: str, entity_id: str):
        deleted.append(f"{entity_type}:{entity_id}")
        rows.pop(f"{entity_type}:{entity_id}", None)
        return True

    monkeypatch.setattr(catalog_service, "find_registry_entity", _find_registry_entity)
    monkeypatch.setattr(catalog_service, "delete_registry_entity", _delete_registry_entity)

    with pytest.raises(catalog_service.CatalogError) as exc_info:
        catalog_service.delete_catalog_agent(
            "ignored",
            agent_id="agent.knowledge_chat",
            actor_user_id=1,
            actor_role="superadmin",
        )

    assert exc_info.value.code == "platform_agent_delete_blocked"

    with pytest.raises(catalog_service.CatalogError) as forbidden_info:
        catalog_service.delete_catalog_agent(
            "ignored",
            agent_id="agent.user",
            actor_user_id=9,
            actor_role="user",
        )

    assert forbidden_info.value.code == "agent_delete_forbidden"

    catalog_service.delete_catalog_agent(
        "ignored",
        agent_id="agent.user",
        actor_user_id=7,
        actor_role="user",
    )

    assert deleted == ["agent:agent.user"]


def test_validate_catalog_agent_checks_model_and_tool_runtime_constraints(monkeypatch: pytest.MonkeyPatch):
    tool_rows = {
        "tool.web_search": {
            "entity_id": "tool.web_search",
            "entity_type": "tool",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "published_at": "2026-01-01T00:00:00+00:00",
            "current_spec": {
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
        },
        "tool.python_exec": {
            "entity_id": "tool.python_exec",
            "entity_type": "tool",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "published",
            "current_version": "v1",
            "published_at": "2026-01-01T00:00:00+00:00",
            "current_spec": {
                "name": "Python exec",
                "description": "desc",
                "transport": "sandbox_http",
                "connection_profile_ref": "default",
                "tool_name": "python_exec",
                "input_schema": {},
                "output_schema": {},
                "safety_policy": {},
                "offline_compatible": True,
            },
        },
    }

    monkeypatch.setattr(
        catalog_service,
        "find_registry_entity",
        lambda _db, *, entity_type, entity_id: {
            "entity_id": "agent.alpha",
            "entity_type": "agent",
            "owner_user_id": 1,
            "visibility": "private",
            "status": "draft",
            "current_version": "v1",
            "published_at": None,
            "current_spec": {
                "name": "Agent Alpha",
                "description": "desc",
                "instructions": "be concise",
                "default_model_ref": "missing-model",
                "tool_refs": [entity_id] if entity_type == "tool" else ["tool.web_search", "tool.python_exec"],
                "runtime_constraints": {"internet_required": False, "sandbox_required": False},
            },
        }
        if entity_type == "agent"
        else tool_rows.get(entity_id),
    )
    monkeypatch.setattr(catalog_service, "find_model_definition", lambda _db, model_id: None)

    result = catalog_service.validate_catalog_agent("ignored", agent_id="agent.alpha")

    assert result["validation"]["valid"] is False
    assert "Model 'missing-model' does not exist." in result["validation"]["errors"]
    assert "Agent references online-only tools but runtime_constraints.internet_required is false." in result["validation"]["errors"]
    assert "Agent references sandbox tools but runtime_constraints.sandbox_required is false." in result["validation"]["errors"]
    assert result["validation"]["derived_runtime_requirements"]["internet_required"] is True
    assert result["validation"]["derived_runtime_requirements"]["sandbox_required"] is True


def test_validate_catalog_tool_requires_active_runtime_and_discovers_mcp_tools(monkeypatch: pytest.MonkeyPatch):
    tool_row = {
        "entity_id": "tool.web_search",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "draft",
        "current_version": "v1",
        "published_at": None,
        "current_spec": {
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
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    class HealthyMcpAdapter:
        def health(self):
            return {"reachable": True, "status_code": 200}

        def list_tools(self):
            return {"tools": [{"tool_name": "web_search"}]}, 200

    result_ok = None
    monkeypatch.setattr(catalog_service, "resolve_mcp_runtime_adapter", lambda _db, config: HealthyMcpAdapter())
    result_ok = catalog_service.validate_catalog_tool("ignored", config=SimpleNamespace(), tool_id="tool.web_search")

    assert result_ok["validation"]["valid"] is True
    assert result_ok["validation"]["runtime_checks"]["tool_discovered"] is True

    monkeypatch.setattr(
        catalog_service,
        "resolve_mcp_runtime_adapter",
        lambda _db, config: (_ for _ in ()).throw(
            PlatformControlPlaneError("missing_active_binding", "Active platform runtime is missing capability 'mcp_runtime'", status_code=404)
        ),
    )
    result_missing = catalog_service.validate_catalog_tool("ignored", config=SimpleNamespace(), tool_id="tool.web_search")

    assert result_missing["validation"]["valid"] is False
    assert "Active platform runtime is missing capability 'mcp_runtime'" in result_missing["validation"]["errors"]


def test_execute_catalog_tool_invokes_mcp_runtime(monkeypatch: pytest.MonkeyPatch):
    tool_row = {
        "entity_id": "tool.web_search",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "published_at": "2026-01-01T00:00:00+00:00",
        "current_spec": {
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
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    captured: dict[str, object] = {}

    class HealthyMcpAdapter:
        def invoke(self, *, tool_name: str, arguments: dict[str, object], request_metadata: dict[str, object]):
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments
            captured["request_metadata"] = request_metadata
            return {"results": [{"title": "Example"}]}, 200

    monkeypatch.setattr(catalog_service, "resolve_mcp_runtime_adapter", lambda _db, config: HealthyMcpAdapter())

    result = catalog_service.execute_catalog_tool(
        "ignored",
        config=SimpleNamespace(),
        tool_id="tool.web_search",
        payload={"input": {"query": "OpenAI", "top_k": 3}},
        actor_user_id=7,
    )

    assert captured == {
        "tool_name": "web_search",
        "arguments": {"query": "OpenAI", "top_k": 3},
        "request_metadata": {"actor_user_id": 7},
    }
    assert result["execution"]["ok"] is True
    assert result["execution"]["result"]["results"][0]["title"] == "Example"


def test_execute_catalog_tool_invokes_sandbox_runtime(monkeypatch: pytest.MonkeyPatch):
    tool_row = {
        "entity_id": "tool.python_exec",
        "entity_type": "tool",
        "owner_user_id": 1,
        "visibility": "private",
        "status": "published",
        "current_version": "v1",
        "published_at": "2026-01-01T00:00:00+00:00",
        "current_spec": {
            "name": "Python exec",
            "description": "desc",
            "transport": "sandbox_http",
            "connection_profile_ref": "default",
            "tool_name": "python_exec",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {"timeout_seconds": 5, "network_access": False},
            "offline_compatible": True,
        },
    }
    monkeypatch.setattr(catalog_service, "find_registry_entity", lambda _db, *, entity_type, entity_id: tool_row)

    captured: dict[str, object] = {}

    class HealthySandboxAdapter:
        def execute(self, *, code: str, language: str, input_payload, timeout_seconds: int, policy: dict[str, object]):
            captured["code"] = code
            captured["language"] = language
            captured["input_payload"] = input_payload
            captured["timeout_seconds"] = timeout_seconds
            captured["policy"] = policy
            return {"stdout": "3\n", "stderr": "", "result": 3}, 200

    monkeypatch.setattr(catalog_service, "resolve_sandbox_execution_adapter", lambda _db, config: HealthySandboxAdapter())

    result = catalog_service.execute_catalog_tool(
        "ignored",
        config=SimpleNamespace(),
        tool_id="tool.python_exec",
        payload={"input": {"code": "print(1 + 2)", "input": {"value": 2}}},
        actor_user_id=7,
    )

    assert captured == {
        "code": "print(1 + 2)",
        "language": "python",
        "input_payload": {"value": 2},
        "timeout_seconds": 5,
        "policy": {"timeout_seconds": 5, "network_access": False},
    }
    assert result["execution"]["ok"] is True
    assert result["execution"]["result"]["result"] == 3
