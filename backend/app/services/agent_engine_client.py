from __future__ import annotations

from json import dumps, loads
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..schemas.agent_executions import AgentExecutionRecord

_DEFAULT_HTTP_TIMEOUT_SECONDS = 3.0


class AgentEngineClientError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _request_json(
    *,
    method: str,
    url: str,
    service_token: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    headers = {
        "Content-Type": "application/json",
        "X-Service-Token": service_token,
        "X-Request-Id": request_id,
    }
    body = dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            status_code = int(response.status)
            raw = response.read().decode("utf-8")
            parsed = loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else {}, status_code
    except HTTPError as error:
        raw = error.read().decode("utf-8")
        parsed = loads(raw) if raw else {}
        if not isinstance(parsed, dict):
            parsed = {}
        code = str(parsed.get("error", "agent_engine_error"))
        message = str(parsed.get("message", "Agent engine request failed"))
        raise AgentEngineClientError(
            code=code,
            message=message,
            status_code=int(error.code),
            details=parsed,
        ) from error
    except URLError as error:
        raise AgentEngineClientError(
            code="agent_engine_unreachable",
            message="Agent engine unavailable",
            status_code=502,
        ) from error


def create_execution(
    *,
    base_url: str,
    service_token: str,
    request_id: str,
    agent_id: str,
    execution_input: dict[str, Any],
    requested_by_user_id: int,
    requested_by_role: str,
    runtime_profile: str,
    org_id: str | None = None,
    group_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    payload: dict[str, Any] = {
        "agent_id": agent_id,
        "input": execution_input,
        "requested_by_user_id": requested_by_user_id,
        "requested_by_role": requested_by_role,
        "runtime_profile": runtime_profile,
    }
    if org_id:
        payload["org_id"] = org_id
    if group_id:
        payload["group_id"] = group_id

    parsed, status_code = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/v1/internal/agent-executions",
        payload=payload,
        service_token=service_token,
        request_id=request_id,
    )
    execution_payload = parsed.get("execution")
    if not isinstance(execution_payload, dict):
        raise AgentEngineClientError(
            code="invalid_engine_response",
            message="Agent engine response missing execution payload",
            status_code=502,
        )
    execution = AgentExecutionRecord.from_payload(execution_payload)
    return {"execution": execution.to_payload()}, status_code


def get_execution(
    *,
    base_url: str,
    service_token: str,
    request_id: str,
    execution_id: str,
) -> tuple[dict[str, Any], int]:
    parsed, status_code = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/v1/internal/agent-executions/{execution_id}",
        service_token=service_token,
        request_id=request_id,
    )
    execution_payload = parsed.get("execution")
    if not isinstance(execution_payload, dict):
        raise AgentEngineClientError(
            code="invalid_engine_response",
            message="Agent engine response missing execution payload",
            status_code=502,
        )
    execution = AgentExecutionRecord.from_payload(execution_payload)
    return {"execution": execution.to_payload()}, status_code
