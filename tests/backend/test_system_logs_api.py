from __future__ import annotations

from app.api.http import system_logs as system_logs_routes
from app.security import hash_password
from app.services import service_logs
from tests.backend.support.auth_harness import auth_header, login


def _login_as_role(backend_test_client_factory, *, role: str) -> tuple[object, str]:
    test_client, user_store, _config = backend_test_client_factory()
    user_store.create_user(
        "postgresql://ignored",
        email=f"{role}@example.com",
        username=role,
        password_hash=hash_password("pass-123"),
        role=role,
        is_active=True,
    )
    token = login(test_client, role, "pass-123").get_json()["access_token"]
    return test_client, token


def test_system_log_services_requires_superadmin_role(backend_test_client_factory):
    test_client, admin_token = _login_as_role(backend_test_client_factory, role="admin")

    response = test_client.get("/v1/system/logs/services", headers=auth_header(admin_token))

    assert response.status_code == 403
    assert response.get_json()["error"] == "insufficient_role"


def test_system_log_services_lists_allowlisted_services(backend_test_client_factory, monkeypatch):
    test_client, token = _login_as_role(backend_test_client_factory, role="superadmin")
    monkeypatch.setattr(
        system_logs_routes.service_logs,
        "list_available_services",
        lambda: [{"id": "backend", "display_name": "Backend"}],
    )

    response = test_client.get("/v1/system/logs/services", headers=auth_header(token))

    assert response.status_code == 200
    assert response.get_json() == {"services": [{"id": "backend", "display_name": "Backend"}]}


def test_system_log_snapshot_rejects_unknown_service(backend_test_client_factory):
    test_client, token = _login_as_role(backend_test_client_factory, role="superadmin")

    response = test_client.get("/v1/system/logs/not-a-service", headers=auth_header(token))

    assert response.status_code == 404
    assert response.get_json()["error"] == "unknown_service"


def test_system_log_snapshot_returns_normalized_entries(backend_test_client_factory, monkeypatch):
    test_client, token = _login_as_role(backend_test_client_factory, role="superadmin")
    monkeypatch.setattr(
        system_logs_routes.service_logs,
        "get_service_log_snapshot",
        lambda service, **_kwargs: {
            "service": service,
            "display_name": "Backend",
            "tail": 200,
            "entries": [
                {
                    "id": "backend-1",
                    "service": "backend",
                    "timestamp": "2026-05-25T10:00:00Z",
                    "level": "error",
                    "event_type": "http",
                    "raw": "2026-05-25T10:00:00Z [ERROR] GET /health failed",
                    "message": "[ERROR] GET /health failed",
                }
            ],
        },
    )

    response = test_client.get("/v1/system/logs/backend?tail=200", headers=auth_header(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service"] == "backend"
    assert payload["entries"][0]["timestamp"] == "2026-05-25T10:00:00Z"
    assert payload["entries"][0]["level"] == "error"
    assert payload["entries"][0]["event_type"] == "http"


def test_system_log_snapshot_returns_unavailable_error(backend_test_client_factory, monkeypatch):
    test_client, token = _login_as_role(backend_test_client_factory, role="superadmin")

    def _raise(*_args, **_kwargs):
        raise service_logs.ServiceLogsError("service_logs_unavailable", "Docker logs are unavailable.", status_code=503)

    monkeypatch.setattr(system_logs_routes.service_logs, "get_service_log_snapshot", _raise)

    response = test_client.get("/v1/system/logs/backend", headers=auth_header(token))

    assert response.status_code == 503
    assert response.get_json()["error"] == "service_logs_unavailable"


def test_system_log_sse_stream_emits_events_and_keepalives(backend_test_client_factory, monkeypatch):
    test_client, token = _login_as_role(backend_test_client_factory, role="superadmin")

    def _stream(*_args, **_kwargs):
        yield {
            "id": "backend-1",
            "service": "backend",
            "timestamp": "2026-05-25T10:00:00Z",
            "level": "info",
            "event_type": "startup",
            "raw": "2026-05-25T10:00:00Z Starting backend",
            "message": "Starting backend",
        }
        yield None

    monkeypatch.setattr(system_logs_routes.service_logs, "stream_service_log_entries", _stream)

    response = test_client.get(
        "/v1/system/logs/backend/events",
        headers=auth_header(token),
        buffered=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "event: service_log" in body
    assert '"id":"backend-1"' in body
    assert ": keepalive" in body


def test_service_log_entry_parser_extracts_timestamp_level_and_event_type():
    entry = service_logs._build_log_entry(  # noqa: SLF001
        "backend",
        "2026-05-25T10:00:00.123456Z [ERROR] GET /health failed",
        index=0,
    )

    assert entry["timestamp"] == "2026-05-25T10:00:00.123456Z"
    assert entry["level"] == "error"
    assert entry["event_type"] == "health"
    assert entry["message"] == "[ERROR] GET /health failed"


def test_service_log_entry_parser_falls_back_to_generic_when_unstructured():
    entry = service_logs._build_log_entry("backend", "plain unstructured output", index=0)  # noqa: SLF001

    assert entry["timestamp"] is None
    assert entry["level"] == "unknown"
    assert entry["event_type"] == "generic"
    assert entry["raw"] == "plain unstructured output"
