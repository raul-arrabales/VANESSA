from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.agent_projects_service import (
    AgentProjectError,
    create_agent_project,
    get_agent_project_detail,
    list_agent_projects,
    publish_agent_project,
    update_agent_project,
    validate_agent_project,
)
from ...authz import require_role
from ...config import get_auth_config

bp = Blueprint("agent_projects", __name__)


def _database_url() -> str:
    return get_auth_config().database_url


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


@bp.get("/v1/agent-projects")
@require_role("user")
def list_agent_projects_route():
    projects = list_agent_projects(
        _database_url(),
        actor_user_id=int(g.current_user["id"]),
        actor_role=str(g.current_user.get("role", "user")),
    )
    return jsonify({"agent_projects": projects}), 200


@bp.post("/v1/agent-projects")
@require_role("user")
def create_agent_project_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        project = create_agent_project(
            _database_url(),
            payload=payload,
            owner_user_id=int(g.current_user["id"]),
        )
    except AgentProjectError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent_project": project}), 201


@bp.get("/v1/agent-projects/<project_id>")
@require_role("user")
def get_agent_project_route(project_id: str):
    try:
        project = get_agent_project_detail(
            _database_url(),
            project_id=project_id,
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
        )
    except AgentProjectError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent_project": project}), 200


@bp.put("/v1/agent-projects/<project_id>")
@require_role("user")
def update_agent_project_route(project_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        project = update_agent_project(
            _database_url(),
            project_id=project_id,
            payload=payload,
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
        )
    except AgentProjectError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"agent_project": project}), 200


@bp.post("/v1/agent-projects/<project_id>/validate")
@require_role("user")
def validate_agent_project_route(project_id: str):
    try:
        payload = validate_agent_project(
            _database_url(),
            project_id=project_id,
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
        )
    except AgentProjectError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.post("/v1/agent-projects/<project_id>/publish")
@require_role("user")
def publish_agent_project_route(project_id: str):
    try:
        payload = publish_agent_project(
            _database_url(),
            project_id=project_id,
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
        )
    except AgentProjectError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200
