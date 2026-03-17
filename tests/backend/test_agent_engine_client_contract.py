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

    monkeypatch.setattr(
        agent_engine_client,
        "_request_json",
        lambda **kwargs: seen_payloads.append(kwargs["payload"]) or (_golden_success_payload(), 201),
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
            "input": {"prompt": "hello"},
            "requested_by_user_id": 42,
            "requested_by_role": "user",
            "runtime_profile": "offline",
            "platform_runtime": {
                "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
                "capabilities": {},
            },
        }
    ]


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
