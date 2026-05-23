from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import URLError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_gateway.app import main as mcp_main  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status: int = 200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_request_backend_json_adds_service_token_and_payload(monkeypatch):
    seen: dict[str, object] = {}

    def fake_urlopen(request, timeout: float):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["timeout"] = timeout
        return _FakeResponse({"ok": True}, status=201)

    monkeypatch.setenv("BACKEND_URL", "http://backend.local")
    monkeypatch.setenv("MCP_GATEWAY_SERVICE_TOKEN", "test-token")
    monkeypatch.setattr(mcp_main, "urlopen", fake_urlopen)

    payload, status_code = mcp_main._request_backend_json(
        "/v1/internal/mcp-servers/web_search/invoke",
        method="POST",
        payload={"arguments": {"query": "hello"}},
    )

    assert status_code == 201
    assert payload == {"ok": True}
    assert seen["url"] == "http://backend.local/v1/internal/mcp-servers/web_search/invoke"
    assert seen["method"] == "POST"
    assert seen["headers"]["X-service-token"] == "test-token"
    assert seen["body"] == {"arguments": {"query": "hello"}}
    assert seen["timeout"] == 8.0


def test_request_backend_json_maps_backend_unavailable(monkeypatch):
    def fake_urlopen(_request, timeout: float):
        raise URLError("offline")

    monkeypatch.setattr(mcp_main, "urlopen", fake_urlopen)

    payload, status_code = mcp_main._request_backend_json("/v1/internal/mcp-servers/discover")

    assert payload is None
    assert status_code == 502


def test_query_from_metadata_encodes_identity_scope():
    query = mcp_main._query_from_metadata(
        {
            "agent_id": "agent.local",
            "agent_domain": "research",
            "delegated_user_id": 42,
            "delegated_user_role": "user",
            "ignored": "value",
        }
    )

    assert query == "?agent_id=agent.local&agent_domain=research&delegated_user_id=42&delegated_user_role=user"
