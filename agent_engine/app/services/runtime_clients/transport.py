from __future__ import annotations

from collections.abc import Iterator
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse, RemoteDisconnected
from json import dumps, loads
from queue import LifoQueue
from socket import timeout as socket_timeout
from ssl import SSLError
from threading import Lock
from time import monotonic
from typing import Any, Callable, TypeVar
from urllib.error import URLError
from urllib.parse import urlparse

from .base import RuntimeClientError
from ...services.stream_telemetry import STREAM_DURATION_MEANING_RESPONSE_HEADERS, STREAM_PHASE_RESPONSE_HEADERS

DEFAULT_HTTP_TIMEOUT_SECONDS = 5.0
_RETRYABLE_TRANSPORT_ERRORS = (OSError, RemoteDisconnected, SSLError, socket_timeout)
_RESPONSE_DRAIN_ERRORS = (*_RETRYABLE_TRANSPORT_ERRORS, AttributeError)

JsonRequestFn = Callable[..., tuple[dict[str, Any] | None, int]]
SseRequestFn = Callable[..., Iterator[tuple[str, dict[str, Any]]]]

ErrorType = TypeVar("ErrorType", bound=RuntimeClientError)
ErrorCodeSpec = str | Callable[[int], str]


class StreamRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class _PooledHttpResponse:
    def __init__(
        self,
        response: HTTPResponse,
        *,
        client: "_PooledHttpClient",
        key: tuple[str, str, int],
        connection: HTTPConnection,
    ):
        self._response = response
        self._client = client
        self._key = key
        self._connection = connection
        self.status = int(getattr(response, "status", 0) or 0)
        self.headers = {key.lower(): value for key, value in response.getheaders()}

    def read(self) -> bytes:
        return self._response.read()

    def readline(self) -> bytes:
        return self._response.readline()

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._response.getheader(name, default)

    def __enter__(self) -> "_PooledHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            try:
                self._response.read()
            except _RESPONSE_DRAIN_ERRORS:
                self._client.discard(self._connection)
                return False
            if self._response.isclosed():
                self._client.release(self._key, self._connection)
                return False
        self._client.discard(self._connection)
        return False


class _PooledHttpClient:
    def __init__(self, *, max_idle_per_origin: int = 8):
        self._max_idle_per_origin = max_idle_per_origin
        self._pools: dict[tuple[str, str, int], LifoQueue[HTTPConnection]] = {}
        self._lock = Lock()

    def request(
        self,
        url: str,
        *,
        method: str,
        data: bytes | None,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> _PooledHttpResponse:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise URLError("Runtime URL is missing or invalid")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        key = (parsed.scheme, parsed.hostname, port)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        last_error: BaseException | None = None
        for attempt in range(2):
            connection = self._acquire(key, timeout_seconds)
            try:
                connection.request(method.upper(), target, body=data, headers=headers)
                return _PooledHttpResponse(connection.getresponse(), client=self, key=key, connection=connection)
            except _RETRYABLE_TRANSPORT_ERRORS as exc:
                last_error = exc
                self.discard(connection)
                if attempt == 0:
                    continue
                raise URLError(str(exc)) from exc
        raise URLError(str(last_error or "request failed"))

    def _acquire(self, key: tuple[str, str, int], timeout_seconds: float) -> HTTPConnection:
        with self._lock:
            pool = self._pools.setdefault(key, LifoQueue(maxsize=self._max_idle_per_origin))
            while not pool.empty():
                connection = pool.get_nowait()
                connection.timeout = timeout_seconds
                sock = getattr(connection, "sock", None)
                if sock is not None:
                    sock.settimeout(timeout_seconds)
                    return connection
        scheme, host, port = key
        connection_cls = HTTPSConnection if scheme == "https" else HTTPConnection
        return connection_cls(host, port=port, timeout=timeout_seconds)

    def release(self, key: tuple[str, str, int], connection: HTTPConnection) -> None:
        if getattr(connection, "sock", None) is None:
            return
        with self._lock:
            pool = self._pools.setdefault(key, LifoQueue(maxsize=self._max_idle_per_origin))
            if pool.full():
                self.discard(connection)
                return
            pool.put_nowait(connection)

    def discard(self, connection: HTTPConnection) -> None:
        try:
            connection.close()
        except OSError:
            pass


_HTTP_CLIENT = _PooledHttpClient()


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

    try:
        with _HTTP_CLIENT.request(
            url,
            method=method,
            data=data,
            headers=request_headers,
            timeout_seconds=timeout_seconds,
        ) as response:
            raw = response.read().decode("utf-8")
            if int(response.status) >= 400:
                try:
                    parsed = loads(raw) if raw else {"error": "upstream_error"}
                except ValueError:
                    parsed = {"error": "upstream_error", "body": raw}
                return parsed, int(response.status)
            if not raw:
                return {}, int(response.status)
            try:
                return loads(raw), int(response.status)
            except ValueError:
                return {"body": raw}, int(response.status)
    except (TimeoutError, socket_timeout):
        return None, 504
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

    started = monotonic()
    try:
        with _HTTP_CLIENT.request(
            url,
            method=method,
            data=data,
            headers=request_headers,
            timeout_seconds=timeout_seconds,
        ) as response:
            if int(response.status) >= 400:
                raw = response.read().decode("utf-8")
                try:
                    parsed = loads(raw) if raw else {"error": "upstream_error"}
                except ValueError:
                    parsed = {"error": "upstream_error", "body": raw}
                if not isinstance(parsed, dict):
                    parsed = {"error": "upstream_error", "body": parsed}
                raise StreamRequestError(
                    str(parsed.get("message") or parsed.get("error") or "Upstream stream request failed"),
                    status_code=int(response.status),
                    payload=parsed,
                )
            yield "transport", {
                "phase": STREAM_PHASE_RESPONSE_HEADERS,
                "duration_ms": int((monotonic() - started) * 1000),
                "status_code": int(getattr(response, "status", 0) or 0),
                "endpoint_host": urlparse(url).netloc,
                "duration_meaning": STREAM_DURATION_MEANING_RESPONSE_HEADERS,
            }
            yield from _iter_sse_events(response)
    except (TimeoutError, socket_timeout) as exc:
        raise StreamRequestError("Upstream stream request timed out", status_code=504) from exc
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
