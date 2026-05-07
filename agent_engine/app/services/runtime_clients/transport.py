from __future__ import annotations

from collections.abc import Iterator
from json import dumps, loads
from time import monotonic
from typing import Any, Callable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .base import RuntimeClientError

DEFAULT_HTTP_TIMEOUT_SECONDS = 5.0

JsonRequestFn = Callable[..., tuple[dict[str, Any] | None, int]]
SseRequestFn = Callable[..., Iterator[tuple[str, dict[str, Any]]]]

ErrorType = TypeVar("ErrorType", bound=RuntimeClientError)
ErrorCodeSpec = str | Callable[[int], str]


class StreamRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def http_json_request(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | None, int]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = dumps(payload).encode("utf-8")

    request = Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}, int(response.status)
            try:
                return loads(raw), int(response.status)
            except ValueError:
                return {"body": raw}, int(response.status)
    except TimeoutError:
        return None, 504
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = loads(raw) if raw else {"error": "upstream_error"}
        except ValueError:
            parsed = {"error": "upstream_error", "body": raw}
        return parsed, int(exc.code)
    except URLError:
        return None, 502


def stream_sse_request(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> Iterator[tuple[str, dict[str, Any]]]:
    request_headers = {"Accept": "text/event-stream"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = dumps(payload).encode("utf-8")

    req = Request(url, data=data, headers=request_headers, method=method.upper())
    started = monotonic()
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            yield "transport", {
                "phase": "upstream_connected",
                "duration_ms": int((monotonic() - started) * 1000),
                "status_code": int(getattr(response, "status", 0) or 0),
                "endpoint_host": urlparse(url).netloc,
            }
            yield from _iter_sse_events(response)
    except TimeoutError as exc:
        raise StreamRequestError("Upstream stream request timed out", status_code=504) from exc
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = loads(raw) if raw else {"error": "upstream_error"}
        except ValueError:
            parsed = {"error": "upstream_error", "body": raw}
        if not isinstance(parsed, dict):
            parsed = {"error": "upstream_error", "body": parsed}
        raise StreamRequestError(
            str(parsed.get("message") or parsed.get("error") or "Upstream stream request failed"),
            status_code=int(exc.code),
            payload=parsed,
        ) from exc
    except URLError as exc:
        raise StreamRequestError("Upstream stream request failed", status_code=502) from exc


def _iter_sse_events(response: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    event_name = "message"
    data_lines: list[str] = []

    def _flush() -> tuple[str, dict[str, Any]] | None:
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = "message"
            return None
        raw_data = "\n".join(data_lines)
        data_lines = []
        current_event = event_name
        event_name = "message"
        if raw_data.strip() == "[DONE]":
            return current_event, {"raw": "[DONE]"}
        try:
            payload = loads(raw_data) if raw_data else {}
        except ValueError:
            payload = {"raw": raw_data}
        if not isinstance(payload, dict):
            payload = {"data": payload}
        return current_event, payload

    while True:
        raw_line = response.readline()
        if not raw_line:
            flushed = _flush()
            if flushed is not None:
                yield flushed
            return
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            flushed = _flush()
            if flushed is not None:
                yield flushed
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip() or "message"
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())


def request_json_or_raise(
    *,
    request_json: JsonRequestFn,
    error_cls: type[ErrorType],
    binding: dict[str, Any],
    url: str,
    method: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    unavailable_code: ErrorCodeSpec,
    unavailable_message: str,
    request_failed_code: ErrorCodeSpec,
    request_failed_message: str,
) -> tuple[dict[str, Any], int]:
    response_payload, status_code = request_json(
        url,
        method=method,
        payload=payload,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    if response_payload is None:
        raise error_cls(
            code=_resolve_error_code(unavailable_code, status_code),
            message=unavailable_message,
            status_code=status_code,
            details=_error_details(binding, status_code),
        )
    if not 200 <= status_code < 300:
        raise error_cls(
            code=_resolve_error_code(request_failed_code, status_code),
            message=request_failed_message,
            status_code=status_code,
            details=_error_details(binding, status_code, upstream=response_payload),
        )
    return response_payload, status_code


def _resolve_error_code(spec: ErrorCodeSpec, status_code: int) -> str:
    return spec(status_code) if callable(spec) else spec


def _error_details(
    binding: dict[str, Any],
    status_code: int,
    *,
    upstream: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "provider_slug": binding.get("slug"),
        "status_code": status_code,
    }
    if upstream is not None:
        details["upstream"] = upstream
    return details
