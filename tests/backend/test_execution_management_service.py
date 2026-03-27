from __future__ import annotations

import pytest

from app.application import execution_management_service
from app.services.agent_engine_client import AgentEngineClientError


class _Config:
    agent_execution_via_engine = True
    agent_execution_fallback = True
    agent_engine_url = "http://agent-engine:8080"
    agent_engine_service_token = "service-token"


def test_create_agent_execution_rejects_invalid_input() -> None:
    with pytest.raises(execution_management_service.ExecutionManagementRequestError) as exc_info:
        execution_management_service.create_agent_execution_response(
            "postgresql://ignored",
            config=_Config(),
            payload={"agent_id": "agent.alpha", "input": "bad"},
            request_id="req-1",
            requested_by_user_id=5,
            requested_by_role="user",
        )

    assert exc_info.value.code == "invalid_input"


def test_create_agent_execution_returns_fallback_payload_for_transport_errors() -> None:
    payload, status_code = execution_management_service.create_agent_execution_response(
        "postgresql://ignored",
        config=_Config(),
        payload={"agent_id": "agent.alpha", "input": {}},
        request_id="req-2",
        requested_by_user_id=5,
        requested_by_role="user",
        create_execution_fn=lambda **_kwargs: (_ for _ in ()).throw(
            AgentEngineClientError(
                code="agent_engine_unreachable",
                message="Agent engine unavailable",
                status_code=502,
            )
        ),
        get_active_platform_runtime_fn=lambda *_args, **_kwargs: {"deployment_profile": {}, "capabilities": {}},
        resolve_runtime_profile_fn=lambda _database_url: "offline",
    )

    assert status_code == 503
    assert payload["error"] == "EXEC_UPSTREAM_UNAVAILABLE"
    assert payload["details"]["operation"] == "create_execution"


def test_get_agent_execution_rejects_blank_execution_id() -> None:
    with pytest.raises(execution_management_service.ExecutionManagementRequestError) as exc_info:
        execution_management_service.get_agent_execution_response(
            _Config(),
            execution_id=" ",
            request_id="req-3",
        )

    assert exc_info.value.code == "invalid_execution_id"
