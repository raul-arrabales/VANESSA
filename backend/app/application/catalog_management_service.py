from __future__ import annotations

from typing import Any

from ..services.catalog_service import (
    CatalogError,
    create_catalog_agent as _create_catalog_agent,
    create_catalog_tool as _create_catalog_tool,
    delete_catalog_agent as _delete_catalog_agent,
    execute_catalog_tool as _execute_catalog_tool,
    get_catalog_agent as _get_catalog_agent,
    get_catalog_tool as _get_catalog_tool,
    list_catalog_agents as _list_catalog_agents,
    list_catalog_tools as _list_catalog_tools,
    preview_catalog_agent_prompt as _preview_catalog_agent_prompt,
    preview_catalog_agent_prompt_payload as _preview_catalog_agent_prompt_payload,
    update_catalog_agent as _update_catalog_agent,
    update_catalog_tool as _update_catalog_tool,
    validate_catalog_agent as _validate_catalog_agent,
    validate_catalog_tool as _validate_catalog_tool,
)


def _require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CatalogError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def list_catalog_agents(database_url: str) -> list[dict[str, Any]]:
    return _list_catalog_agents(database_url)


def get_catalog_agent(database_url: str, *, agent_id: str) -> dict[str, Any]:
    return _get_catalog_agent(database_url, agent_id=agent_id)


def create_catalog_agent(
    database_url: str,
    *,
    payload: Any,
    owner_user_id: int,
) -> dict[str, Any]:
    return _create_catalog_agent(
        database_url,
        payload=_require_json_object(payload),
        owner_user_id=owner_user_id,
    )


def update_catalog_agent(
    database_url: str,
    *,
    agent_id: str,
    payload: Any,
) -> dict[str, Any]:
    return _update_catalog_agent(
        database_url,
        agent_id=agent_id,
        payload=_require_json_object(payload),
    )


def delete_catalog_agent(
    database_url: str,
    *,
    agent_id: str,
    actor_user_id: int,
    actor_role: str,
) -> None:
    _delete_catalog_agent(
        database_url,
        agent_id=agent_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )


def validate_catalog_agent(database_url: str, *, agent_id: str) -> dict[str, Any]:
    return _validate_catalog_agent(database_url, agent_id=agent_id)


def preview_catalog_agent_prompt(database_url: str, *, agent_id: str) -> dict[str, Any]:
    return _preview_catalog_agent_prompt(database_url, agent_id=agent_id)


def preview_catalog_agent_prompt_payload(payload: Any) -> dict[str, Any]:
    return _preview_catalog_agent_prompt_payload(_require_json_object(payload))


def list_catalog_tools(database_url: str) -> list[dict[str, Any]]:
    return _list_catalog_tools(database_url)


def get_catalog_tool(database_url: str, *, tool_id: str) -> dict[str, Any]:
    return _get_catalog_tool(database_url, tool_id=tool_id)


def create_catalog_tool(
    database_url: str,
    *,
    payload: Any,
    owner_user_id: int,
) -> dict[str, Any]:
    return _create_catalog_tool(
        database_url,
        payload=_require_json_object(payload),
        owner_user_id=owner_user_id,
    )


def update_catalog_tool(
    database_url: str,
    *,
    tool_id: str,
    payload: Any,
) -> dict[str, Any]:
    return _update_catalog_tool(
        database_url,
        tool_id=tool_id,
        payload=_require_json_object(payload),
    )


def validate_catalog_tool(
    database_url: str,
    *,
    config: Any,
    tool_id: str,
) -> dict[str, Any]:
    return _validate_catalog_tool(database_url, config=config, tool_id=tool_id)


def execute_catalog_tool(
    database_url: str,
    *,
    config: Any,
    tool_id: str,
    payload: Any,
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    return _execute_catalog_tool(
        database_url,
        config=config,
        tool_id=tool_id,
        payload=_require_json_object(payload),
        actor_user_id=actor_user_id,
    )
