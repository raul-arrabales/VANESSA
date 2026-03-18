from __future__ import annotations

import pytest

from app.services import registry_service  # noqa: E402


def test_tool_spec_accepts_mcp_transport(monkeypatch: pytest.MonkeyPatch):
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
            "transport": "mcp",
            "connection_profile_ref": "default",
            "tool_name": "web_search",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": False,
        },
        version="v1",
        publish=True,
    )

    assert created["entity"]["entity_type"] == "tool"


def test_tool_spec_accepts_sandbox_transport(monkeypatch: pytest.MonkeyPatch):
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
            "transport": "sandbox_http",
            "connection_profile_ref": "default",
            "tool_name": "python_exec",
            "input_schema": {},
            "output_schema": {},
            "safety_policy": {},
            "offline_compatible": True,
        },
        version="v1",
        publish=True,
    )

    assert created["version"]["version"] == "v1"


def test_tool_spec_rejects_non_default_connection_profile():
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
                "transport": "mcp",
                "connection_profile_ref": "custom",
                "tool_name": "invalid_tool",
                "input_schema": {},
                "output_schema": {},
                "safety_policy": {},
                "offline_compatible": False,
            },
            version="v1",
            publish=False,
        )

    assert str(exc_info.value) == "invalid_connection_profile_ref"
