from __future__ import annotations

from typing import Any

from ..services.catalog_service import (
    CatalogError,
    create_catalog_agent as _create_catalog_agent,
    create_catalog_mcp_server as _create_catalog_mcp_server,
    create_catalog_tool as _create_catalog_tool,
    delete_catalog_agent as _delete_catalog_agent,
    delete_catalog_mcp_server as _delete_catalog_mcp_server,
    discover_authorized_mcp_servers as _discover_authorized_mcp_servers,
    execute_catalog_tool as _execute_catalog_tool,
    get_catalog_agent as _get_catalog_agent,
    get_catalog_defaults as _get_catalog_defaults,
    get_catalog_mcp_server as _get_catalog_mcp_server,
    get_catalog_mcp_creation_options as _get_catalog_mcp_creation_options,
    get_catalog_tool as _get_catalog_tool,
    get_catalog_tool_creation_options as _get_catalog_tool_creation_options,
    invoke_catalog_mcp_server as _invoke_catalog_mcp_server,
    list_catalog_agents as _list_catalog_agents,
    list_catalog_mcp_servers as _list_catalog_mcp_servers,
    list_catalog_tools as _list_catalog_tools,
    preview_catalog_agent_prompt as _preview_catalog_agent_prompt,
    preview_catalog_agent_prompt_payload as _preview_catalog_agent_prompt_payload,
    set_catalog_mcp_server_enabled as _set_catalog_mcp_server_enabled,
    test_catalog_mcp_server as _test_catalog_mcp_server,
    update_catalog_agent as _update_catalog_agent,
    update_catalog_mcp_server as _update_catalog_mcp_server,
    update_catalog_tool as _update_catalog_tool,
    validate_catalog_agent as _validate_catalog_agent,
    validate_catalog_mcp_server as _validate_catalog_mcp_server,
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


def list_catalog_tools(database_url: str, *, config: Any | None = None) -> list[dict[str, Any]]:
    return _list_catalog_tools(database_url, config=config)


def list_catalog_mcp_servers(database_url: str, *, config: Any | None = None) -> list[dict[str, Any]]:
    return _list_catalog_mcp_servers(database_url, config=config)


def get_catalog_defaults() -> dict[str, Any]:
    return _get_catalog_defaults()


def get_catalog_tool_creation_options(database_url: str, *, config: Any) -> dict[str, Any]:
    return _get_catalog_tool_creation_options(database_url, config=config)


def get_catalog_mcp_creation_options(database_url: str, *, config: Any | None = None) -> dict[str, Any]:
    return _get_catalog_mcp_creation_options(database_url, config=config)


def get_catalog_tool(database_url: str, *, tool_id: str) -> dict[str, Any]:
    return _get_catalog_tool(database_url, tool_id=tool_id)


def get_catalog_mcp_server(database_url: str, *, mcp_server_id: str) -> dict[str, Any]:
    return _get_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)


def create_catalog_tool(
    database_url: str,
    *,
    payload: Any,
    owner_user_id: int,
    config: Any | None = None,
) -> dict[str, Any]:
    return _create_catalog_tool(
        database_url,
        payload=_require_json_object(payload),
        owner_user_id=owner_user_id,
        config=config,
    )


def update_catalog_tool(
    database_url: str,
    *,
    tool_id: str,
    payload: Any,
    config: Any | None = None,
) -> dict[str, Any]:
    return _update_catalog_tool(
        database_url,
        tool_id=tool_id,
        payload=_require_json_object(payload),
        config=config,
    )


def create_catalog_mcp_server(
    database_url: str,
    *,
    payload: Any,
    owner_user_id: int,
) -> dict[str, Any]:
    return _create_catalog_mcp_server(
        database_url,
        payload=_require_json_object(payload),
        owner_user_id=owner_user_id,
    )


def update_catalog_mcp_server(
    database_url: str,
    *,
    mcp_server_id: str,
    payload: Any,
) -> dict[str, Any]:
    return _update_catalog_mcp_server(
        database_url,
        mcp_server_id=mcp_server_id,
        payload=_require_json_object(payload),
    )


def delete_catalog_mcp_server(database_url: str, *, mcp_server_id: str) -> None:
    _delete_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)


def set_catalog_mcp_server_enabled(database_url: str, *, mcp_server_id: str, enabled: bool) -> dict[str, Any]:
    return _set_catalog_mcp_server_enabled(database_url, mcp_server_id=mcp_server_id, enabled=enabled)


def validate_catalog_tool(
    database_url: str,
    *,
    config: Any,
    tool_id: str,
) -> dict[str, Any]:
    return _validate_catalog_tool(database_url, config=config, tool_id=tool_id)


def validate_catalog_mcp_server(
    database_url: str,
    *,
    config: Any,
    mcp_server_id: str,
) -> dict[str, Any]:
    return _validate_catalog_mcp_server(database_url, config=config, mcp_server_id=mcp_server_id)


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


def test_catalog_mcp_server(
    database_url: str,
    *,
    config: Any,
    mcp_server_id: str,
    payload: Any,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    return _test_catalog_mcp_server(
        database_url,
        config=config,
        mcp_server_id=mcp_server_id,
        payload=_require_json_object(payload),
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )


def discover_authorized_mcp_servers(
    database_url: str,
    *,
    config: Any | None = None,
    agent_id: str | None,
    agent_domain: str | None,
    delegated_user_id: int | None,
    delegated_user_role: str | None,
) -> list[dict[str, Any]]:
    return _discover_authorized_mcp_servers(
        database_url,
        config=config,
        agent_id=agent_id,
        agent_domain=agent_domain,
        delegated_user_id=delegated_user_id,
        delegated_user_role=delegated_user_role,
    )


def invoke_catalog_mcp_server(
    database_url: str,
    *,
    config: Any,
    slug: str,
    arguments: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    return _invoke_catalog_mcp_server(
        database_url,
        config=config,
        slug=slug,
        arguments=arguments,
        request_metadata=request_metadata,
    )
