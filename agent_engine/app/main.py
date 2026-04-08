from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

try:  # pragma: no cover - import path varies by invocation style
    from .config import get_config
    from .execution_pipeline.runner import create_execution, get_execution
    from .repositories.executions import ensure_schema
    from .services.policy_runtime_gate import ExecutionBlockedError
except ImportError:  # pragma: no cover
    from agent_engine.app.config import get_config
    from agent_engine.app.execution_pipeline.runner import create_execution, get_execution
    from agent_engine.app.repositories.executions import ensure_schema
    from agent_engine.app.services.policy_runtime_gate import ExecutionBlockedError


def _service_token() -> str:
    return get_config().agent_engine_service_token


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAAgentEngine/0.3"

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

    def _is_internal_path(self, path: str) -> bool:
        return path.startswith("/v1/internal/")

    def _authorize_internal(self, path: str) -> bool:
        if not self._is_internal_path(path):
            return True
        token = self.headers.get("X-Service-Token", "").strip()
        if not token or token != _service_token():
            self._send_json(401, {"error": "invalid_service_token", "message": "Missing or invalid service token"})
            return False
        return True

    def _route_path(self) -> str:
        path = urlparse(self.path).path
        if path.startswith("/v1/internal/"):
            return "/v1/" + path.removeprefix("/v1/internal/")
        return path

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "agent_engine"})
            return
        if not self._authorize_internal(path):
            return

        route_path = self._route_path()
        if route_path.startswith("/v1/agent-executions/"):
            execution_id = route_path.split("/")[-1].strip()
            if not execution_id:
                self._send_json(400, {"error": "invalid_execution_id", "message": "execution_id is required"})
                return
            try:
                payload, status = get_execution(execution_id)
                self._send_json(status, payload)
            except ValueError:
                self._send_json(400, {"error": "invalid_execution_id", "message": "execution_id is required"})
            except ExecutionBlockedError as exc:
                self._send_json(exc.status_code, {"error": exc.code, "message": exc.message, "details": exc.details})
            return

        self._send_json(404, {"error": "not_found", "message": "Route not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._authorize_internal(path):
            return
        route_path = self._route_path()

        if route_path != "/v1/agent-executions":
            self._send_json(404, {"error": "not_found", "message": "Route not found"})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return

        try:
            response_payload, status_code = create_execution(payload)
            self._send_json(status_code, response_payload)
        except ValueError as exc:
            code = str(exc)
            if code == "invalid_agent_id":
                self._send_json(400, {"error": "invalid_agent_id", "message": "agent_id is required"})
                return
            if code == "invalid_input":
                self._send_json(400, {"error": "invalid_input", "message": "input must be an object when provided"})
                return
            if code == "invalid_retrieval_input":
                self._send_json(
                    400,
                    {
                        "error": "invalid_retrieval_input",
                        "message": (
                            "retrieval must include a valid index, explicit or derived query text, "
                            "positive top_k, scalar filters, and valid search_method, "
                            "query_preprocessing, and hybrid_alpha values when provided"
                        ),
                    },
                )
                return
            self._send_json(400, {"error": "invalid_payload", "message": "Expected valid payload"})
        except ExecutionBlockedError as exc:
            self._send_json(exc.status_code, {"error": exc.code, "message": exc.message, "details": exc.details})


if __name__ == "__main__":
    ensure_schema()
    server = HTTPServer(("0.0.0.0", 7000), Handler)
    server.serve_forever()
