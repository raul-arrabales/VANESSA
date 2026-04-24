from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import quote_plus


DEFAULT_MCP_GATEWAY_PORT = 8080


def _web_search(arguments: dict[str, Any]) -> tuple[dict[str, Any], int]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return {"error": "invalid_arguments", "message": "query is required"}, 400
    top_k_raw = arguments.get("top_k", 3)
    try:
        top_k = int(top_k_raw)
    except (TypeError, ValueError):
        return {"error": "invalid_arguments", "message": "top_k must be an integer"}, 400
    top_k = max(1, min(top_k, 10))
    results = [
        {
            "title": f"Search result {index} for {query}",
            "snippet": f"Synthetic MCP gateway result {index} for query '{query}'.",
            "url": f"https://search.local/{quote_plus(query)}/{index}",
        }
        for index in range(1, top_k + 1)
    ]
    return {"query": query, "results": results}, 200


_TOOLS: dict[str, dict[str, Any]] = {
    "web_search": {
        "description": "Searches the web through the MCP gateway runtime.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "invoke": _web_search,
    }
}


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAMcpGateway/0.1"

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
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "mcp_gateway"})
            return
        if self.path == "/v1/tools":
            self._send_json(
                200,
                {
                    "tools": [
                        {
                            "tool_name": tool_name,
                            "description": tool["description"],
                            "input_schema": tool["input_schema"],
                        }
                        for tool_name, tool in sorted(_TOOLS.items())
                    ]
                },
            )
            return
        self._send_json(404, {"error": "not_found", "message": "Route not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/tools/invoke":
            self._send_json(404, {"error": "not_found", "message": "Route not found"})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return

        tool_name = str(payload.get("tool_name", "")).strip()
        tool = _TOOLS.get(tool_name)
        if tool is None:
            self._send_json(404, {"error": "tool_not_found", "message": "Tool not found"})
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

        result, status_code = tool["invoke"](arguments)
        self._send_json(
            status_code,
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "request_metadata": request_metadata,
                "result": result if status_code < 400 else None,
                "error": result if status_code >= 400 else None,
            },
        )


if __name__ == "__main__":
    port = int(os.getenv("MCP_GATEWAY_PORT", str(DEFAULT_MCP_GATEWAY_PORT)) or DEFAULT_MCP_GATEWAY_PORT)
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
