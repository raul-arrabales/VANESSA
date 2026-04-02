from __future__ import annotations

from json import dumps, loads
from typing import Any, Callable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import RuntimeClientError

DEFAULT_HTTP_TIMEOUT_SECONDS = 5.0

JsonRequestFn = Callable[..., tuple[dict[str, Any] | None, int]]

ErrorType = TypeVar("ErrorType", bound=RuntimeClientError)
ErrorCodeSpec = str | Callable[[int], str]


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
