from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_MCP_GATEWAY_PORT = 8080
DEFAULT_BACKEND_URL = "http://backend:5000"
DEFAULT_MCP_GATEWAY_SERVICE_TOKEN = "dev-mcp-gateway-token"
DEFAULT_SEARXNG_URL = "http://searxng:8080"
DEFAULT_SEARXNG_TIMEOUT_SECONDS = 8.0
_VALID_TIME_RANGES = {"day", "month", "year"}
_VALID_SAFESEARCH_VALUES = {"0", "1", "2"}


def _env_float(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _optional_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _backend_url() -> str:
    return (os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip() or DEFAULT_BACKEND_URL).rstrip("/")


def _service_token() -> str:
    return os.getenv("MCP_GATEWAY_SERVICE_TOKEN", DEFAULT_MCP_GATEWAY_SERVICE_TOKEN).strip() or DEFAULT_MCP_GATEWAY_SERVICE_TOKEN


def _coerce_top_k(value: Any) -> tuple[int | None, dict[str, str] | None]:
    try:
        top_k = int(value)
    except (TypeError, ValueError):
        return None, {"error": "invalid_arguments", "message": "top_k must be an integer"}
    return max(1, min(top_k, 10)), None


def _coerce_safesearch(value: Any) -> tuple[str | None, dict[str, str] | None]:
    raw = _optional_string(value)
    if not raw:
        raw = _optional_string(os.getenv("SEARXNG_DEFAULT_SAFESEARCH", "1"))
    if raw not in _VALID_SAFESEARCH_VALUES:
        return None, {"error": "invalid_arguments", "message": "safesearch must be one of 0, 1, or 2"}
    return raw, None


def _coerce_time_range(value: Any) -> tuple[str | None, dict[str, str] | None]:
    raw = _optional_string(value)
    if not raw:
        return None, None
    if raw not in _VALID_TIME_RANGES:
        return None, {"error": "invalid_arguments", "message": "time_range must be one of day, month, or year"}
    return raw, None


def _searxng_search_url(arguments: dict[str, Any], *, query: str) -> tuple[str | None, dict[str, str] | None]:
    safesearch, error = _coerce_safesearch(arguments.get("safesearch"))
    if error:
        return None, error
    time_range, error = _coerce_time_range(arguments.get("time_range"))
    if error:
        return None, error

    language = _optional_string(arguments.get("language")) or _optional_string(os.getenv("SEARXNG_DEFAULT_LANGUAGE", ""))
    categories = _optional_string(arguments.get("categories")) or _optional_string(os.getenv("SEARXNG_DEFAULT_CATEGORIES", ""))
    engines = _optional_string(os.getenv("SEARXNG_DEFAULT_ENGINES", ""))
    base_url = (_optional_string(os.getenv("SEARXNG_URL")) or DEFAULT_SEARXNG_URL).rstrip("/")
    params: dict[str, str] = {
        "q": query,
        "format": "json",
        "safesearch": safesearch or "1",
    }
    if language:
        params["language"] = language
    if categories:
        params["categories"] = categories
    if engines:
        params["engines"] = engines
    if time_range:
        params["time_range"] = time_range
    return f"{base_url}/search?{urlencode(params)}", None


def _fetch_json(url: str, *, timeout_seconds: float) -> tuple[dict[str, Any] | None, int]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}, int(response.status)
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"results": []}, int(response.status)
    except TimeoutError:
        return None, 504
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {"error": "searxng_http_error"}
        except ValueError:
            parsed = {"error": "searxng_http_error", "body": raw}
        return parsed if isinstance(parsed, dict) else {"error": "searxng_http_error"}, int(exc.code)
    except (URLError, OSError):
        return None, 502
    except ValueError:
        return {"error": "invalid_searxng_response", "message": "SearXNG returned non-JSON response"}, 502


def _normalize_engine(value: Any, result: dict[str, Any]) -> str:
    if isinstance(value, str):
        return value
    engines = result.get("engines")
    if isinstance(engines, list):
        return ", ".join(str(item).strip() for item in engines if str(item).strip())
    return ""


def _normalize_results(payload: dict[str, Any], *, top_k: int) -> list[dict[str, Any]]:
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return []
    normalized: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = _optional_string(item.get("url"))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        normalized.append(
            {
                "title": _optional_string(item.get("title")),
                "url": url,
                "snippet": _optional_string(item.get("content") or item.get("snippet")),
                "engine": _normalize_engine(item.get("engine"), item),
                "rank": len(normalized) + 1,
            }
        )
        if len(normalized) >= top_k:
            break
    return normalized


def _web_search(arguments: dict[str, Any]) -> tuple[dict[str, Any], int]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return {"error": "invalid_arguments", "message": "query is required"}, 400
    top_k, error = _coerce_top_k(arguments.get("top_k", 3))
    if error:
        return error, 400
    assert top_k is not None
    search_url, error = _searxng_search_url(arguments, query=query)
    if error:
        return error, 400
    assert search_url is not None

    timeout_seconds = _env_float("SEARXNG_TIMEOUT_SECONDS", DEFAULT_SEARXNG_TIMEOUT_SECONDS)
    payload, status_code = _fetch_json(search_url, timeout_seconds=timeout_seconds)
    if payload is None:
        error_code = "search_timeout" if status_code == 504 else "search_backend_unavailable"
        return {"error": error_code, "message": "SearXNG search backend is unavailable"}, status_code
    if not 200 <= status_code < 300:
        return {
            "error": "search_backend_error",
            "message": "SearXNG search backend returned an error",
            "upstream_status_code": status_code,
            "upstream": payload,
        }, status_code
    return {"query": query, "results": _normalize_results(payload, top_k=top_k)}, 200


def _request_backend_json(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, int]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json",
        "X-Service-Token": _service_token(),
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(_backend_url() + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8.0) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else {}, int(response.status)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {"error": "backend_error"}
        except ValueError:
            parsed = {"error": "backend_error", "body": raw}
        return parsed if isinstance(parsed, dict) else {"error": "backend_error"}, int(exc.code)
    except (TimeoutError, URLError, OSError):
        return None, 502


def _query_from_metadata(metadata: dict[str, Any]) -> str:
    params: dict[str, str] = {}
    for source_key, param_key in [
        ("agent_id", "agent_id"),
        ("agent_domain", "agent_domain"),
        ("delegated_user_id", "delegated_user_id"),
        ("delegated_user_role", "delegated_user_role"),
    ]:
        value = _optional_string(metadata.get(source_key))
        if value:
            params[param_key] = value
    return f"?{urlencode(params)}" if params else ""


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAMcpGateway/0.2"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _authorize_internal(self) -> bool:
        token = self.headers.get("X-Service-Token", "").strip()
        if not token or token != _service_token():
            self._send_json(401, {"error": "invalid_service_token", "message": "Missing or invalid service token"})
            return False
        return True

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "service": "mcp_gateway"})
            return
        if parsed.path == "/v1/tools":
            payload, status_code = _request_backend_json(f"/v1/internal/mcp-servers/discover?{parsed.query}" if parsed.query else "/v1/internal/mcp-servers/discover")
            if payload is None:
                self._send_json(502, {"error": "backend_unavailable", "message": "Backend MCP registry is unavailable"})
                return
            self._send_json(status_code, payload)
            return
        self._send_json(404, {"error": "not_found", "message": "Route not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/v1/internal/tools/web-search":
            if not self._authorize_internal():
                return
            payload = self._read_json()
            if payload is None:
                self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
                return
            arguments = payload.get("arguments", {})
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                self._send_json(400, {"error": "invalid_arguments", "message": "arguments must be an object"})
                return
            result, status_code = _web_search(arguments)
            self._send_json(status_code, result)
            return

        if parsed.path != "/v1/tools/invoke":
            self._send_json(404, {"error": "not_found", "message": "Route not found"})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return
        arguments = payload.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            self._send_json(400, {"error": "invalid_arguments", "message": "arguments must be an object"})
            return
        request_metadata = payload.get("request_metadata", {})
        if request_metadata is None:
            request_metadata = {}
        if not isinstance(request_metadata, dict):
            self._send_json(400, {"error": "invalid_request_metadata", "message": "request_metadata must be an object"})
            return

        server_slug = _optional_string(request_metadata.get("mcp_server_slug")) or _optional_string(payload.get("server_slug")) or _optional_string(payload.get("tool_name"))
        if not server_slug:
            self._send_json(400, {"error": "invalid_mcp_server", "message": "MCP server slug is required"})
            return
        backend_payload, status_code = _request_backend_json(
            f"/v1/internal/mcp-servers/{server_slug}/invoke",
            method="POST",
            payload={
                "arguments": arguments,
                "request_metadata": request_metadata,
            },
        )
        if backend_payload is None:
            self._send_json(502, {"error": "backend_unavailable", "message": "Backend MCP invocation is unavailable"})
            return
        self._send_json(status_code, backend_payload)


if __name__ == "__main__":
    port = int(os.getenv("MCP_GATEWAY_PORT", str(DEFAULT_MCP_GATEWAY_PORT)) or DEFAULT_MCP_GATEWAY_PORT)
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
