from __future__ import annotations

import pytest

from app.services import registry_service  # noqa: E402


def test_agent_spec_requires_runtime_prompts():
    with pytest.raises(ValueError) as exc_info:
        registry_service.create_entity_with_version(
            "ignored",
            entity_type="agent",
            entity_id="agent.alpha",
            owner_user_id=1,
            visibility="private",
            spec={
                "name": "Agent Alpha",
                "description": "test agent",
                "instructions": "be concise",
                "default_model_ref": "model.default",
                "tool_refs": [],
                "runtime_constraints": {"internet_required": False, "sandbox_required": True},
            },
            version="v1",
            publish=False,
        )

    assert str(exc_info.value) == "missing_agent_field:runtime_prompts"


def test_agent_spec_rejects_empty_runtime_prompt():
    with pytest.raises(ValueError) as exc_info:
        registry_service.create_entity_with_version(
            "ignored",
            entity_type="agent",
            entity_id="agent.alpha",
            owner_user_id=1,
            visibility="private",
            spec={
                "name": "Agent Alpha",
                "description": "test agent",
                "instructions": "be concise",
                "runtime_prompts": {"retrieval_context": ""},
                "default_model_ref": "model.default",
                "tool_refs": [],
                "runtime_constraints": {"internet_required": False, "sandbox_required": True},
            },
            version="v1",
            publish=False,
        )

    assert str(exc_info.value) == "invalid_agent_field:runtime_prompts.retrieval_context is required"


def test_workflow_agent_spec_accepts_empty_runtime_prompt(monkeypatch: pytest.MonkeyPatch):
    created_specs: list[dict[str, object]] = []

    monkeypatch.setattr(
        registry_service,
        "create_registry_entity",
        lambda *_args, **_kwargs: {"entity_id": "agent.workflow", "entity_type": "agent"},
    )
    monkeypatch.setattr(
        registry_service,
        "create_registry_version",
        lambda *_args, spec_json, **_kwargs: created_specs.append(spec_json) or {"entity_id": "agent.workflow", "version": "v1"},
    )

    created = registry_service.create_entity_with_version(
        "ignored",
        entity_type="agent",
        entity_id="agent.workflow",
        owner_user_id=1,
        visibility="private",
        spec={
            "name": "Workflow Agent",
            "description": "workflow agent",
            "instructions": "",
            "runtime_prompts": {"retrieval_context": ""},
            "default_model_ref": "model.default",
            "tool_refs": [],
            "agent_type": "workflow",
            "runtime_constraints": {"internet_required": False, "sandbox_required": True},
        },
        version="v1",
        publish=False,
    )

    assert created["entity"]["entity_type"] == "agent"
    assert created_specs[0]["runtime_prompts"] == {"retrieval_context": ""}


def test_tool_spec_accepts_web_search_execution_backend(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        registry_service,
        "create_registry_entity",
        lambda *_args, **_kwargs: {"entity_id": "tool.web_search", "entity_type": "tool"},
    )
    monkeypatch.setattr(
        registry_service,
        "create_registry_version",
        lambda *_args, **_kwargs: {"entity_id": "tool.web_search", "version": "v1"},
    )

    created = registry_service.create_entity_with_version(
        "ignored",
        entity_type="tool",
        entity_id="tool.web_search",
        owner_user_id=1,
        visibility="private",
        spec={
            "name": "Web Search",
            "description": "Search the web",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
            "execution_backend": "web_search",
            "execution_config": {},
            "permissions": {},
        },
        version="v1",
        publish=True,
    )

    assert created["entity"]["entity_type"] == "tool"


def test_tool_spec_accepts_sandbox_execution_backend(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        registry_service,
        "create_registry_entity",
        lambda *_args, **_kwargs: {"entity_id": "tool.python_exec", "entity_type": "tool"},
    )
    monkeypatch.setattr(
        registry_service,
        "create_registry_version",
        lambda *_args, **_kwargs: {"entity_id": "tool.python_exec", "version": "v1"},
    )

    created = registry_service.create_entity_with_version(
        "ignored",
        entity_type="tool",
        entity_id="tool.python_exec",
        owner_user_id=1,
        visibility="private",
        spec={
            "name": "Python Execution",
            "description": "Run Python",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": True,
            "execution_backend": "sandbox_python",
            "execution_config": {},
            "permissions": {},
        },
        version="v1",
        publish=True,
    )

    assert created["version"]["version"] == "v1"


def test_tool_spec_rejects_missing_execution_backend():
    with pytest.raises(ValueError) as exc_info:
        registry_service.create_entity_with_version(
            "ignored",
            entity_type="tool",
            entity_id="tool.invalid",
            owner_user_id=1,
            visibility="private",
            spec={
                "name": "Invalid Tool",
                "description": "Invalid",
                "input_schema": {},
                "output_schema": {},
                "safety_policy": {},
                "offline_compatible": False,
            },
            version="v1",
            publish=False,
        )

    assert str(exc_info.value) == "missing_tool_field:execution_backend"
