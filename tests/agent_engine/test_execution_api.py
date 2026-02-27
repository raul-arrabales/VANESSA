from __future__ import annotations

import json
import sys
import threading
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from agent_engine.app import main as module
from contract_fixtures import load_contract_fixture


def _request_json(method: str, host: str, port: int, path: str, body: dict | None = None, headers: dict | None = None):
    conn = HTTPConnection(host, port, timeout=3)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    merged_headers = {"Content-Type": "application/json"} if body is not None else {}
    if headers:
        merged_headers.update(headers)
    conn.request(method, path, body=payload, headers=merged_headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    conn.close()
    return response.status, parsed


def test_execution_create_and_get_roundtrip():
    try:
        server = HTTPServer(("127.0.0.1", 0), module.Handler)
    except PermissionError:
        pytest.skip("Socket binding is not permitted in this test environment")
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        status, created = _request_json(
            "POST",
            host,
            port,
            "/v1/agent-executions",
            {"agent_id": "agent.alpha", "runtime_profile": "offline", "input": {"prompt": "hello"}},
        )
        assert status == 201
        execution = created["execution"]
        assert execution["agent_ref"] == "agent.alpha"
        assert execution["status"] == "succeeded"

        execution_id = execution["id"]
        get_status, fetched = _request_json("GET", host, port, f"/v1/agent-executions/{execution_id}")
        assert get_status == 200
        assert fetched["execution"]["id"] == execution_id
        assert fetched["execution"]["status"] == "succeeded"
    finally:
        server.shutdown()
        server.server_close()


def test_internal_endpoint_requires_service_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_ENGINE_SERVICE_TOKEN", "test-token")
    try:
        server = HTTPServer(("127.0.0.1", 0), module.Handler)
    except PermissionError:
        pytest.skip("Socket binding is not permitted in this test environment")
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        missing_status, _ = _request_json(
            "POST",
            host,
            port,
            "/v1/internal/agent-executions",
            {"agent_id": "agent.alpha", "runtime_profile": "offline", "input": {}},
        )
        assert missing_status == 401

        ok_status, payload = _request_json(
            "POST",
            host,
            port,
            "/v1/internal/agent-executions",
            {"agent_id": "agent.alpha", "runtime_profile": "offline", "input": {}},
            headers={"X-Service-Token": "test-token"},
        )
        assert ok_status == 201
        assert payload["execution"]["agent_ref"] == "agent.alpha"
    finally:
        server.shutdown()
        server.server_close()


def test_engine_success_payload_matches_golden_shape(monkeypatch: pytest.MonkeyPatch):
    golden = load_contract_fixture("agent_execution", "succeeded_execution.json")["execution"]
    monkeypatch.setattr(
        module,
        "create_execution",
        lambda _payload: ({"execution": dict(golden)}, 201),
    )

    try:
        server = HTTPServer(("127.0.0.1", 0), module.Handler)
    except PermissionError:
        pytest.skip("Socket binding is not permitted in this test environment")
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, created = _request_json(
            "POST",
            host,
            port,
            "/v1/agent-executions",
            {"agent_id": "agent.alpha", "runtime_profile": "offline", "input": {"prompt": "hello"}},
        )
        assert status == 201
        assert set(created["execution"].keys()) == set(golden.keys())
    finally:
        server.shutdown()
        server.server_close()
