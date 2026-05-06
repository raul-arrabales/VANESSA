from __future__ import annotations

from json import dumps, loads
from typing import Any, Iterator
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
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], int]:
    headers = {
        "Content-Type": "application/json",
        "X-Service-Token": service_token,
        "X-Request-Id": request_id,
    }
    body = dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            raw = response.read().decode("utf-8")
            parsed = loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else {}, status_code
    except TimeoutError as error:
        raise AgentEngineClientError(
            code="agent_engine_timeout",
            message="Agent engine timed out",
            status_code=504,
        ) from error
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


def _parse_sse_event(raw_event: str) -> dict[str, Any] | None:
    event_name = "message"
    data_lines: list[str] = []
    for line in raw_event.replace("\r", "").split("\n"):
        if not line or line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip() or "message"
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").lstrip())
    if not data_lines:
        return None
    parsed = loads("\n".join(data_lines))
    return {"event": event_name, "data": parsed if isinstance(parsed, dict) else {}}


def _request_sse(
    *,
    url: str,
    service_token: str,
    request_id: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> Iterator[dict[str, Any]]:
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "X-Service-Token": service_token,
        "X-Request-Id": request_id,
    }
    req = Request(url, data=dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            buffer = ""
            while True:
                chunk = response.read(1)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")
                boundary = buffer.find("\n\n")
                while boundary >= 0:
                    raw_event = buffer[:boundary]
                    buffer = buffer[boundary + 2 :]
                    parsed = _parse_sse_event(raw_event)
                    if parsed is not None:
                        yield parsed
                    boundary = buffer.find("\n\n")
            if buffer.strip():
                parsed = _parse_sse_event(buffer)
                if parsed is not None:
                    yield parsed
    except TimeoutError as error:
        raise AgentEngineClientError(
            code="agent_engine_timeout",
            message="Agent engine timed out",
            status_code=504,
        ) from error
    except HTTPError as error:
        raw = error.read().decode("utf-8")
        parsed = loads(raw) if raw else {}
        if not isinstance(parsed, dict):
            parsed = {}
        raise AgentEngineClientError(
            code=str(parsed.get("error", "agent_engine_error")),
            message=str(parsed.get("message", "Agent engine request failed")),
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
    platform_runtime: dict[str, Any],
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
    org_id: str | None = None,
    group_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    payload: dict[str, Any] = {
        "agent_id": agent_id,
        "input": execution_input,
        "requested_by_user_id": requested_by_user_id,
        "requested_by_role": requested_by_role,
        "runtime_profile": runtime_profile,
        "platform_runtime": platform_runtime,
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
        timeout_seconds=timeout_seconds,
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


def stream_execution(
    *,
    base_url: str,
    service_token: str,
    request_id: str,
    agent_id: str,
    execution_input: dict[str, Any],
    requested_by_user_id: int,
    requested_by_role: str,
    runtime_profile: str,
    platform_runtime: dict[str, Any],
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
    org_id: str | None = None,
    group_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    payload: dict[str, Any] = {
        "agent_id": agent_id,
        "input": execution_input,
        "requested_by_user_id": requested_by_user_id,
        "requested_by_role": requested_by_role,
        "runtime_profile": runtime_profile,
        "platform_runtime": platform_runtime,
    }
    if org_id:
        payload["org_id"] = org_id
    if group_id:
        payload["group_id"] = group_id

    for event in _request_sse(
        url=f"{base_url.rstrip('/')}/v1/internal/agent-executions/stream",
        payload=payload,
        service_token=service_token,
        request_id=request_id,
        timeout_seconds=timeout_seconds,
    ):
        event_name = str(event.get("event") or "").strip()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_name == "complete":
            execution_payload = data.get("execution")
            if not isinstance(execution_payload, dict):
                raise AgentEngineClientError(
                    code="invalid_engine_response",
                    message="Agent engine response missing execution payload",
                    status_code=502,
                )
            execution = AgentExecutionRecord.from_payload(execution_payload)
            yield {"event": "complete", "data": {"execution": execution.to_payload()}}
            continue
        yield {"event": event_name, "data": data}


def get_execution(
    *,
    base_url: str,
    service_token: str,
    request_id: str,
    execution_id: str,
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], int]:
    parsed, status_code = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/v1/internal/agent-executions/{execution_id}",
        service_token=service_token,
        request_id=request_id,
        timeout_seconds=timeout_seconds,
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
