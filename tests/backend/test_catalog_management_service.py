from __future__ import annotations

import pytest

from app.application import catalog_management_service


def test_create_catalog_agent_requires_json_object() -> None:
    with pytest.raises(catalog_management_service.CatalogError) as exc_info:
        catalog_management_service.create_catalog_agent(
            "postgresql://ignored",
            payload=[],
            owner_user_id=10,
        )

    assert exc_info.value.code == "invalid_payload"


def test_validate_catalog_tool_passes_config_through(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _validate_tool(_database_url: str, *, config, tool_id: str):
        captured["config"] = config
        captured["tool_id"] = tool_id
        return {"tool": {"id": tool_id}, "validation": {"valid": True, "errors": [], "warnings": [], "runtime_checks": {}}}

    monkeypatch.setattr(catalog_management_service, "_validate_catalog_tool", _validate_tool)

    payload = catalog_management_service.validate_catalog_tool(
        "postgresql://ignored",
        config="config",
        tool_id="tool.web_search",
    )

    assert captured == {
        "config": "config",
        "tool_id": "tool.web_search",
    }
    assert payload["validation"]["valid"] is True


def test_execute_catalog_tool_requires_json_object() -> None:
    with pytest.raises(catalog_management_service.CatalogError) as exc_info:
        catalog_management_service.execute_catalog_tool(
            "postgresql://ignored",
            config="config",
            tool_id="tool.web_search",
            payload=[],
            actor_user_id=10,
        )

    assert exc_info.value.code == "invalid_payload"
