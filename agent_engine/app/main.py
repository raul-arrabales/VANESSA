from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

_EXECUTIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAAgentEngine/0.1"

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

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "service": "agent_engine"})
            return

        if parsed.path.startswith("/v1/agent-executions/"):
            execution_id = parsed.path.split("/")[-1].strip()
            if not execution_id:
                self._send_json(400, {"error": "invalid_execution_id", "message": "execution_id is required"})
                return
            with _LOCK:
                execution = _EXECUTIONS.get(execution_id)
            if execution is None:
                self._send_json(404, {"error": "execution_not_found", "message": "Execution not found"})
                return
            self._send_json(200, {"execution": execution})
            return

        self._send_json(404, {"error": "not_found", "message": "Route not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/v1/agent-executions":
            self._send_json(404, {"error": "not_found", "message": "Route not found"})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return

        agent_id = str(payload.get("agent_id", "")).strip()
        if not agent_id:
            self._send_json(400, {"error": "invalid_agent_id", "message": "agent_id is required"})
            return

        runtime_profile = str(payload.get("runtime_profile", "offline")).strip().lower() or "offline"
        execution_id = str(uuid4())
        now = _iso_now()

        # Phase-1 execution scaffold: resolve/request metadata and return deterministic simulated output.
        output_text = f"Agent '{agent_id}' executed in {runtime_profile} profile"
        execution = {
            "id": execution_id,
            "agent_id": agent_id,
            "status": "succeeded",
            "runtime_profile": runtime_profile,
            "requested_by_user_id": payload.get("requested_by_user_id"),
            "input": payload.get("input") if isinstance(payload.get("input"), dict) else {},
            "result": {
                "output_text": output_text,
                "tool_calls": [],
                "model_calls": [],
            },
            "created_at": now,
            "updated_at": now,
        }

        with _LOCK:
            _EXECUTIONS[execution_id] = execution

        self._send_json(201, {"execution": execution})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 7000), Handler)
    server.serve_forever()
