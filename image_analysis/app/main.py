from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .constants import DEFAULT_PORT, ROLE_GATEWAY, VALID_ROLES
from .gateway import health_for_role, resources_payload_for_role
from .runtime import analyze_for_role


def _service_role() -> str:
    role = os.getenv("IMAGE_ANALYSIS_ROLE", ROLE_GATEWAY).strip().lower() or ROLE_GATEWAY
    return role if role in VALID_ROLES else ROLE_GATEWAY


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        return None
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAImageAnalysis/0.1"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        role = _service_role()
        if self.path == "/health":
            self._send_json(health_for_role(role))
            return
        if self.path == "/v1/resources":
            self._send_json(resources_payload_for_role(role))
            return
        self._send_json({"error": "not_found", "message": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/v1/analyze":
            self._send_json({"error": "not_found", "message": "Not found"}, 404)
            return
        role = _service_role()
        payload = _read_json(self)
        if payload is None:
            self._send_json({"error": "invalid_payload", "message": "Expected JSON object"}, 400)
            return
        result, status = analyze_for_role(payload, role)
        self._send_json(result, status)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        if os.getenv("IMAGE_ANALYSIS_ACCESS_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)


def main() -> None:
    port = int(os.getenv("IMAGE_ANALYSIS_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"image_analysis role={_service_role()} listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
