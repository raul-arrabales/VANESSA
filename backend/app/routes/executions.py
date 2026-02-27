from __future__ import annotations

import os
from json import dumps, loads
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..services.policy_service import PolicyDeniedError, require_entity_permission
from ..services.registry_service import get_entity
from ..services.runtime_profile_service import internet_allowed, resolve_runtime_profile

bp = Blueprint("executions", __name__)

_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


def _http_json_request(url: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    req = Request(
        url,
        data=dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            status_code = int(response.status)
            body = response.read().decode("utf-8")
            return (loads(body) if body else {}), status_code
    except HTTPError as error:
        body = error.read().decode("utf-8")
        parsed = loads(body) if body else {"error": "upstream_error"}
        return parsed, int(error.code)
    except URLError:
        return None, 502


def _http_get_json(url: str) -> tuple[dict[str, Any] | None, int]:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            status_code = int(response.status)
            body = response.read().decode("utf-8")
            return (loads(body) if body else {}), status_code
    except HTTPError as error:
        body = error.read().decode("utf-8")
        parsed = loads(body) if body else {"error": "upstream_error"}
        return parsed, int(error.code)
    except URLError:
        return None, 502


@bp.post("/v1/agent-executions")
@require_role("user")
def create_agent_execution():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    agent_id = str(payload.get("agent_id", "")).strip()
    execution_input = payload.get("input")
    if not agent_id:
        return _json_error(400, "invalid_agent_id", "agent_id is required")

    database_url = _database_url()
    agent_entity = get_entity(database_url, entity_type="agent", entity_id=agent_id)
    if agent_entity is None:
        return _json_error(404, "agent_not_found", "Agent not found in registry")

    try:
        require_entity_permission(
            database_url=database_url,
            current_user=g.current_user,
            entity_id=agent_id,
            required_permission="execute",
        )
    except PolicyDeniedError as exc:
        return _json_error(403, "policy_denied", str(exc))

    runtime_profile = resolve_runtime_profile(database_url)
    current_spec = (
        agent_entity.get("current_spec")
        if isinstance(agent_entity.get("current_spec"), dict)
        else {}
    )
    runtime_constraints = (
        current_spec.get("runtime_constraints")
        if isinstance(current_spec.get("runtime_constraints"), dict)
        else {}
    )
    internet_required = bool(runtime_constraints.get("internet_required", False))
    if internet_required and not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Agent '{agent_id}' requires internet but runtime profile is '{runtime_profile}'",
        )

    tool_refs = current_spec.get("tool_refs") if isinstance(current_spec.get("tool_refs"), list) else []
    if runtime_profile != "online":
        for tool_ref in tool_refs:
            tool_id = str(tool_ref).strip()
            if not tool_id:
                continue
            tool_entity = get_entity(database_url, entity_type="tool", entity_id=tool_id)
            if tool_entity is None:
                return _json_error(422, "tool_not_found", f"Tool '{tool_id}' referenced by agent does not exist")
            tool_spec = (
                tool_entity.get("current_spec")
                if isinstance(tool_entity.get("current_spec"), dict)
                else {}
            )
            if not bool(tool_spec.get("offline_compatible", False)):
                return _json_error(
                    403,
                    "runtime_profile_blocks_tool",
                    f"Tool '{tool_id}' is not offline-compatible for profile '{runtime_profile}'",
                )

    upstream_payload: dict[str, Any] = {
        "agent_id": agent_id,
        "input": execution_input if isinstance(execution_input, dict) else {},
        "requested_by_user_id": int(g.current_user["id"]),
        "runtime_profile": runtime_profile,
    }
    for key in ("org_id", "group_id"):
        value = str(payload.get(key, "")).strip()
        if value:
            upstream_payload[key] = value

    agent_engine_url = os.getenv("AGENT_ENGINE_URL", "http://agent_engine:7000").rstrip("/")
    response_payload, status_code = _http_json_request(
        f"{agent_engine_url}/v1/agent-executions",
        upstream_payload,
    )
    if response_payload is None:
        return _json_error(502, "agent_engine_unreachable", "Agent engine unavailable")
    return jsonify(response_payload), status_code


@bp.get("/v1/agent-executions/<execution_id>")
@require_role("user")
def get_agent_execution(execution_id: str):
    if not execution_id.strip():
        return _json_error(400, "invalid_execution_id", "execution_id is required")

    agent_engine_url = os.getenv("AGENT_ENGINE_URL", "http://agent_engine:7000").rstrip("/")
    response_payload, status_code = _http_get_json(
        f"{agent_engine_url}/v1/agent-executions/{execution_id.strip()}",
    )
    if response_payload is None:
        return _json_error(502, "agent_engine_unreachable", "Agent engine unavailable")
    return jsonify(response_payload), status_code
