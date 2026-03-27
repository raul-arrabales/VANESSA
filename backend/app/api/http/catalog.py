from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.catalog_management_service import (
    CatalogError,
    create_catalog_agent,
    create_catalog_tool,
    get_catalog_agent,
    get_catalog_tool,
    list_catalog_agents,
    list_catalog_tools,
    update_catalog_agent,
    update_catalog_tool,
    validate_catalog_agent,
    validate_catalog_tool,
)
from ...authz import require_role
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


@bp.get("/v1/catalog/agents/<agent_id>")
@require_role("superadmin")
def get_catalog_agent_route(agent_id: str):
    try:
        agent = get_catalog_agent(_database_url(), agent_id=agent_id)
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent": agent}), 200


@bp.put("/v1/catalog/agents/<agent_id>")
@require_role("superadmin")
def update_catalog_agent_route(agent_id: str):
    try:
        agent = update_catalog_agent(_database_url(), agent_id=agent_id, payload=request.get_json(silent=True))
    except CatalogError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent": agent}), 200


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
