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
            "default_model_ref": "safe-small",
            "tool_refs": [],
            "runtime_constraints": {"internet_required": False, "sandbox_required": False},
        },
    )

    assert created["current_version"] == "v1"
    assert created["published"] is False
    assert updated["current_version"] == "v2"
    assert updated["published"] is True
    assert updated["status"] == "published"


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
