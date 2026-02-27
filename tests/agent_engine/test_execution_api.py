from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
import importlib.util
import pytest


def _load_agent_engine_main():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "agent_engine" / "app" / "main.py"
    spec = importlib.util.spec_from_file_location("vanessa_agent_engine_main", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _request_json(method: str, host: str, port: int, path: str, body: dict | None = None):
    conn = HTTPConnection(host, port, timeout=3)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=payload, headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    conn.close()
    return response.status, parsed


def test_execution_create_and_get_roundtrip():
    module = _load_agent_engine_main()
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
        assert execution["agent_id"] == "agent.alpha"
        assert execution["status"] == "succeeded"

        execution_id = execution["id"]
        get_status, fetched = _request_json("GET", host, port, f"/v1/agent-executions/{execution_id}")
        assert get_status == 200
        assert fetched["execution"]["id"] == execution_id
    finally:
        server.shutdown()
        server.server_close()
