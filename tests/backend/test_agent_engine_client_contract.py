from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.services import agent_engine_client  # noqa: E402


def _sample_execution() -> dict[str, object]:
    return {
        "id": "exec-1",
        "status": "succeeded",
        "agent_ref": "agent.alpha",
        "agent_version": "v1",
        "model_ref": None,
        "runtime_profile": "offline",
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "result": {"output_text": "ok"},
        "error": None,
    }


def test_create_execution_validates_contract(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        agent_engine_client,
        "_request_json",
        lambda **_kwargs: ({"execution": _sample_execution()}, 201),
    )

    payload, status = agent_engine_client.create_execution(
        base_url="http://agent_engine:7000",
        service_token="token",
        request_id="req-1",
        agent_id="agent.alpha",
        execution_input={"prompt": "hello"},
        requested_by_user_id=42,
        requested_by_role="user",
        runtime_profile="offline",
    )
    assert status == 201
    assert payload["execution"]["id"] == "exec-1"


def test_get_execution_validates_contract(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        agent_engine_client,
        "_request_json",
        lambda **_kwargs: ({"execution": _sample_execution()}, 200),
    )
    payload, status = agent_engine_client.get_execution(
        base_url="http://agent_engine:7000",
        service_token="token",
        request_id="req-2",
        execution_id="exec-1",
    )
    assert status == 200
    assert payload["execution"]["agent_ref"] == "agent.alpha"


def test_invalid_engine_payload_returns_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(agent_engine_client, "_request_json", lambda **_kwargs: ({}, 201))
    with pytest.raises(agent_engine_client.AgentEngineClientError) as exc:
        agent_engine_client.create_execution(
            base_url="http://agent_engine:7000",
            service_token="token",
            request_id="req-3",
            agent_id="agent.alpha",
            execution_input={},
            requested_by_user_id=1,
            requested_by_role="user",
            runtime_profile="offline",
        )
    assert exc.value.code == "invalid_engine_response"
