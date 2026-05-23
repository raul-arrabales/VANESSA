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


def _optional_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _backend_url() -> str:
    return (os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip() or DEFAULT_BACKEND_URL).rstrip("/")


def _service_token() -> str:
    return os.getenv("MCP_GATEWAY_SERVICE_TOKEN", DEFAULT_MCP_GATEWAY_SERVICE_TOKEN).strip() or DEFAULT_MCP_GATEWAY_SERVICE_TOKEN


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
            parsed = json.loads(raw) if raw else {"error": "backend_http_error"}
        except ValueError:
            parsed = {"error": "backend_http_error", "body": raw}
        return parsed if isinstance(parsed, dict) else {"error": "backend_http_error"}, int(exc.code)
    except (URLError, OSError):
        return None, 502
    except ValueError:
        return {"error": "invalid_backend_response", "message": "Backend returned non-JSON response"}, 502


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
