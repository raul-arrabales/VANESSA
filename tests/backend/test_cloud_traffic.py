from __future__ import annotations

import json
from types import SimpleNamespace

from app.api.http import runtime as runtime_routes
from app.security import hash_password
from app.services import cloud_traffic
from tests.backend.support.auth_harness import auth_header, login


def test_cloud_traffic_event_sanitization_uses_allowlist():
    event = cloud_traffic.sanitize_cloud_traffic_event(
        {
            "direction": "egress",
            "phase": "request_sent",
            "headers": {"Authorization": "Bearer secret"},
            "payload": {"prompt": "secret prompt"},
            "api_key": "secret",
            "endpoint_host": "https://api.openai.com/v1/chat/completions",
            "status_code": "200",
        }
    )

    assert event["direction"] == "egress"
    assert event["endpoint_host"] == "api.openai.com"
    assert event["status_code"] == 200
    assert "headers" not in event
    assert "payload" not in event
    assert "api_key" not in event


def test_cloud_traffic_jsonl_writer_appends_and_rotates(tmp_path):
    log_path = tmp_path / "cloud-traffic.jsonl"
    config = SimpleNamespace(
        cloud_traffic_log_enabled=True,
        cloud_traffic_log_path=str(log_path),
        cloud_traffic_log_max_bytes=80,
    )

    first = cloud_traffic.publish_cloud_traffic_event(
        {"direction": "egress", "phase": "request_sent", "source_service": "backend"},
        config=config,
    )
    log_path.write_text("x" * 81, encoding="utf-8")
    second = cloud_traffic.publish_cloud_traffic_event(
        {"direction": "ingress", "phase": "response_received", "source_service": "backend"},
        config=config,
    )

    assert (tmp_path / "cloud-traffic.jsonl.1").exists()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == second["id"]
    assert first["direction"] == "egress"


def test_cloud_traffic_subscriber_receives_published_event():
    with cloud_traffic.subscribe_cloud_traffic_events() as queue:
        published = cloud_traffic.publish_cloud_traffic_event(
            {"direction": "egress", "phase": "request_sent", "source_service": "backend"}
        )

        assert queue.get(timeout=1)["id"] == published["id"]


def test_internal_cloud_traffic_endpoint_requires_service_token(backend_test_client_factory):
    test_client, _user_store, _config = backend_test_client_factory(
        config_overrides={"agent_engine_service_token": "test-token", "cloud_traffic_log_enabled": False}
    )

    missing = test_client.post("/v1/internal/cloud-traffic/events", json={"direction": "egress"})
    accepted = test_client.post(
        "/v1/internal/cloud-traffic/events",
        headers={"X-Service-Token": "test-token"},
        json={"direction": "egress", "phase": "request_sent", "source_service": "agent_engine"},
    )

    assert missing.status_code == 401
    assert accepted.status_code == 202
    assert accepted.get_json()["event"]["source_service"] == "agent_engine"


def test_cloud_traffic_sse_stream_emits_events(backend_test_client_factory, monkeypatch):
    test_client, user_store, _config = backend_test_client_factory(
        config_overrides={"cloud_traffic_log_enabled": False}
    )
    user_store.create_user(
        "postgresql://ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = login(test_client, "root", "root-pass-123").get_json()["access_token"]

    def _stream():
        yield {
            "id": "event-1",
            "timestamp": "2026-05-08T00:00:00Z",
            "direction": "ingress",
            "phase": "response_received",
            "runtime_profile": "online",
            "source_service": "backend",
        }

    monkeypatch.setattr(runtime_routes, "stream_cloud_traffic_events", _stream)

    response = test_client.get(
        "/v1/runtime/cloud-traffic/events",
        headers=auth_header(token),
        buffered=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "event: cloud_traffic" in body
    assert '"id":"event-1"' in body
