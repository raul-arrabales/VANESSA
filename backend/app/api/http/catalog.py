from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.catalog_management_service import (
    CatalogError,
    create_catalog_agent,
    create_catalog_mcp_server,
    create_catalog_tool,
    delete_catalog_agent,
    delete_catalog_mcp_server,
    discover_authorized_mcp_servers,
    execute_catalog_tool,
    get_catalog_agent,
    get_catalog_defaults,
    get_catalog_mcp_server,
    get_catalog_tool,
    invoke_catalog_mcp_server,
    list_catalog_agents,
    list_catalog_mcp_servers,
    list_catalog_tools,
    preview_catalog_agent_prompt,
    preview_catalog_agent_prompt_payload,
    set_catalog_mcp_server_enabled,
    test_catalog_mcp_server,
    update_catalog_agent,
    update_catalog_mcp_server,
    update_catalog_tool,
    validate_catalog_agent,
    validate_catalog_mcp_server,
    validate_catalog_tool,
)
from ...authz import require_auth, require_role
from ...config import get_auth_config

bp = Blueprint("catalog", __name__)


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


def _int_arg(name: str) -> int | None:
    value = request.args.get(name)
    if value in {None, ""}:
        return None
    try:
        parsed = int(str(value))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _authorize_mcp_gateway() -> bool:
    token = request.headers.get("X-Service-Token", "").strip()
    return bool(token and token == _config().mcp_gateway_service_token)


@bp.get("/v1/catalog/defaults")
@require_auth
def get_catalog_defaults_route():
    try:
        defaults = get_catalog_defaults()
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"defaults": defaults}), 200


@bp.get("/v1/catalog/agents")
@require_role("superadmin")
def list_catalog_agents_route():
    try:
        agents = list_catalog_agents(_database_url())
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agents": agents}), 200


@bp.post("/v1/catalog/agents")
@require_role("superadmin")
def create_catalog_agent_route():
    try:
        agent = create_catalog_agent(_database_url(), payload=request.get_json(silent=True), owner_user_id=int(g.current_user["id"]))
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent": agent}), 201


@bp.post("/v1/catalog/agents/prompt-preview")
@require_role("superadmin")
def preview_catalog_agent_prompt_payload_route():
    try:
        payload = preview_catalog_agent_prompt_payload(request.get_json(silent=True))
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/catalog/agents/<agent_id>")
@require_role("superadmin")
def get_catalog_agent_route(agent_id: str):
    try:
        agent = get_catalog_agent(_database_url(), agent_id=agent_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent": agent}), 200


@bp.get("/v1/catalog/agents/<agent_id>/prompt-preview")
@require_role("superadmin")
def preview_catalog_agent_prompt_route(agent_id: str):
    try:
        payload = preview_catalog_agent_prompt(_database_url(), agent_id=agent_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.put("/v1/catalog/agents/<agent_id>")
@require_role("superadmin")
def update_catalog_agent_route(agent_id: str):
    try:
        agent = update_catalog_agent(_database_url(), agent_id=agent_id, payload=request.get_json(silent=True))
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent": agent}), 200


@bp.delete("/v1/catalog/agents/<agent_id>")
@require_auth
def delete_catalog_agent_route(agent_id: str):
    try:
        delete_catalog_agent(
            _database_url(),
            agent_id=agent_id,
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
        )
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True}), 200


@bp.post("/v1/catalog/agents/<agent_id>/validate")
@require_role("superadmin")
def validate_catalog_agent_route(agent_id: str):
    try:
        payload = validate_catalog_agent(_database_url(), agent_id=agent_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/catalog/tools")
@require_role("superadmin")
def list_catalog_tools_route():
    try:
        tools = list_catalog_tools(_database_url())
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"tools": tools}), 200


@bp.post("/v1/catalog/tools")
@require_role("superadmin")
def create_catalog_tool_route():
    try:
        tool = create_catalog_tool(_database_url(), payload=request.get_json(silent=True), owner_user_id=int(g.current_user["id"]))
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"tool": tool}), 201


@bp.get("/v1/catalog/tools/<tool_id>")
@require_role("superadmin")
def get_catalog_tool_route(tool_id: str):
    try:
        tool = get_catalog_tool(_database_url(), tool_id=tool_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"tool": tool}), 200


@bp.put("/v1/catalog/tools/<tool_id>")
@require_role("superadmin")
def update_catalog_tool_route(tool_id: str):
    try:
        tool = update_catalog_tool(_database_url(), tool_id=tool_id, payload=request.get_json(silent=True))
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"tool": tool}), 200


@bp.post("/v1/catalog/tools/<tool_id>/validate")
@require_role("superadmin")
def validate_catalog_tool_route(tool_id: str):
    try:
        payload = validate_catalog_tool(_database_url(), config=_config(), tool_id=tool_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.post("/v1/catalog/tools/<tool_id>/test")
@require_role("superadmin")
def execute_catalog_tool_route(tool_id: str):
    try:
        payload = execute_catalog_tool(
            _database_url(),
            config=_config(),
            tool_id=tool_id,
            payload=request.get_json(silent=True),
            actor_user_id=int(g.current_user["id"]),
        )
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/catalog/mcp-servers")
@require_role("superadmin")
def list_catalog_mcp_servers_route():
    try:
        servers = list_catalog_mcp_servers(_database_url())
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"mcp_servers": servers}), 200


@bp.post("/v1/catalog/mcp-servers")
@require_role("superadmin")
def create_catalog_mcp_server_route():
    try:
        server = create_catalog_mcp_server(
            _database_url(),
            payload=request.get_json(silent=True),
            owner_user_id=int(g.current_user["id"]),
        )
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"mcp_server": server}), 201


@bp.get("/v1/catalog/mcp-servers/<mcp_server_id>")
@require_role("superadmin")
def get_catalog_mcp_server_route(mcp_server_id: str):
    try:
        server = get_catalog_mcp_server(_database_url(), mcp_server_id=mcp_server_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"mcp_server": server}), 200


@bp.put("/v1/catalog/mcp-servers/<mcp_server_id>")
@require_role("superadmin")
def update_catalog_mcp_server_route(mcp_server_id: str):
    try:
        server = update_catalog_mcp_server(
            _database_url(),
            mcp_server_id=mcp_server_id,
            payload=request.get_json(silent=True),
        )
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"mcp_server": server}), 200


@bp.delete("/v1/catalog/mcp-servers/<mcp_server_id>")
@require_role("superadmin")
def delete_catalog_mcp_server_route(mcp_server_id: str):
    try:
        delete_catalog_mcp_server(_database_url(), mcp_server_id=mcp_server_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True}), 200


@bp.post("/v1/catalog/mcp-servers/<mcp_server_id>/validate")
@require_role("superadmin")
def validate_catalog_mcp_server_route(mcp_server_id: str):
    try:
        payload = validate_catalog_mcp_server(_database_url(), config=_config(), mcp_server_id=mcp_server_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.post("/v1/catalog/mcp-servers/<mcp_server_id>/test")
@require_role("superadmin")
def test_catalog_mcp_server_route(mcp_server_id: str):
    try:
        payload = test_catalog_mcp_server(
            _database_url(),
            config=_config(),
            mcp_server_id=mcp_server_id,
            payload=request.get_json(silent=True),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "superadmin")),
        )
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.post("/v1/catalog/mcp-servers/<mcp_server_id>/enable")
@require_role("superadmin")
def enable_catalog_mcp_server_route(mcp_server_id: str):
    try:
        server = set_catalog_mcp_server_enabled(_database_url(), mcp_server_id=mcp_server_id, enabled=True)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"mcp_server": server}), 200


@bp.post("/v1/catalog/mcp-servers/<mcp_server_id>/disable")
@require_role("superadmin")
def disable_catalog_mcp_server_route(mcp_server_id: str):
    try:
        server = set_catalog_mcp_server_enabled(_database_url(), mcp_server_id=mcp_server_id, enabled=False)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"mcp_server": server}), 200


@bp.get("/v1/internal/mcp-servers/discover")
def discover_mcp_servers_internal_route():
    if not _authorize_mcp_gateway():
        return _json_error(401, "invalid_service_token", "Missing or invalid service token")
    servers = discover_authorized_mcp_servers(
        _database_url(),
        agent_id=request.args.get("agent_id"),
        agent_domain=request.args.get("agent_domain"),
        delegated_user_id=_int_arg("delegated_user_id"),
        delegated_user_role=request.args.get("delegated_user_role"),
    )
    return jsonify({"tools": servers}), 200


@bp.post("/v1/internal/mcp-servers/<slug>/invoke")
def invoke_mcp_server_internal_route(slug: str):
    if not _authorize_mcp_gateway():
        return _json_error(401, "invalid_service_token", "Missing or invalid service token")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        return _json_error(400, "invalid_arguments", "arguments must be an object")
    request_metadata = payload.get("request_metadata", {})
    if not isinstance(request_metadata, dict):
        return _json_error(400, "invalid_request_metadata", "request_metadata must be an object")
    result, status_code = invoke_catalog_mcp_server(
        _database_url(),
        config=_config(),
        slug=slug,
        arguments=arguments,
        request_metadata=request_metadata,
    )
    return jsonify(result), status_code
