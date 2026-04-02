from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
TESTS_PATH = PROJECT_ROOT / "tests"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))

from app.services import agent_engine_client  # noqa: E402
from contract_fixtures import load_contract_fixture  # noqa: E402


def _golden_success_payload() -> dict[str, object]:
    return load_contract_fixture("agent_execution", "succeeded_execution.json")


def test_create_execution_validates_contract(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []
    seen_timeouts: list[float] = []

    monkeypatch.setattr(
        agent_engine_client,
        "_request_json",
        lambda **kwargs: seen_payloads.append(kwargs["payload"]) or seen_timeouts.append(kwargs["timeout_seconds"]) or (_golden_success_payload(), 201),
    )

    payload, status = agent_engine_client.create_execution(
        base_url="http://agent_engine:7000",
        service_token="token",
        request_id="req-1",
        agent_id="agent.alpha",
        execution_input={"prompt": "hello", "retrieval": {"index": "knowledge_base", "top_k": 3}},
        requested_by_user_id=42,
        requested_by_role="user",
        runtime_profile="offline",
        platform_runtime={
            "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
            "capabilities": {},
        },
    )
    assert status == 201
    assert payload["execution"]["id"] == "exec-1"
    assert seen_payloads == [
        {
            "agent_id": "agent.alpha",
            "input": {"prompt": "hello", "retrieval": {"index": "knowledge_base", "top_k": 3}},
            "requested_by_user_id": 42,
            "requested_by_role": "user",
            "runtime_profile": "offline",
            "platform_runtime": {
                "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
                "capabilities": {},
            },
        }
    ]
    assert seen_timeouts == [agent_engine_client._DEFAULT_HTTP_TIMEOUT_SECONDS]


def test_create_execution_accepts_explicit_timeout(monkeypatch: pytest.MonkeyPatch):
    seen_timeouts: list[float] = []

    monkeypatch.setattr(
        agent_engine_client,
        "_request_json",
        lambda **kwargs: seen_timeouts.append(kwargs["timeout_seconds"]) or (_golden_success_payload(), 201),
    )

    payload, status = agent_engine_client.create_execution(
        base_url="http://agent_engine:7000",
        service_token="token",
        request_id="req-timeout",
        agent_id="agent.alpha",
        execution_input={"prompt": "hello"},
        requested_by_user_id=42,
        requested_by_role="user",
        runtime_profile="offline",
        platform_runtime={
            "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
            "capabilities": {},
        },
        timeout_seconds=45.0,
    )

    assert status == 201
    assert payload["execution"]["id"] == "exec-1"
    assert seen_timeouts == [45.0]


def test_request_json_maps_transport_timeout_to_agent_engine_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        agent_engine_client,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("timed out")),
    )

    with pytest.raises(agent_engine_client.AgentEngineClientError) as exc:
        agent_engine_client._request_json(
            method="POST",
            url="http://agent_engine:7000/v1/internal/agent-executions",
            service_token="token",
            request_id="req-timeout",
            payload={"agent_id": "agent.alpha"},
            timeout_seconds=12.0,
        )

    assert exc.value.code == "agent_engine_timeout"
    assert exc.value.status_code == 504


def test_get_execution_validates_contract(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        agent_engine_client,
        "_request_json",
        lambda **_kwargs: (_golden_success_payload(), 200),
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
            platform_runtime={
                "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
                "capabilities": {},
            },
        )
    assert exc.value.code == "invalid_engine_response"


def test_error_taxonomy_fixture_is_complete():
    fixture = load_contract_fixture("agent_execution", "error_taxonomy.json")
    expected_codes = {
        "EXEC_POLICY_DENIED",
        "EXEC_RUNTIME_PROFILE_BLOCKED",
        "EXEC_AGENT_NOT_FOUND",
        "EXEC_AGENT_VERSION_NOT_FOUND",
        "EXEC_MODEL_NOT_ALLOWED",
        "EXEC_TOOL_NOT_ALLOWED",
        "EXEC_TIMEOUT",
        "EXEC_UPSTREAM_UNAVAILABLE",
        "EXEC_INTERNAL_ERROR",
    }
    assert set(fixture["codes"]) == expected_codes
