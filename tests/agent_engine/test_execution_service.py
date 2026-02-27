from __future__ import annotations

import sys
from typing import Any
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services import execution_service
from agent_engine.app.services.policy_runtime_gate import ExecutionBlockedError


def test_execution_state_machine_success(monkeypatch: pytest.MonkeyPatch):
    saved_statuses: list[str] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v2", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(
        execution_service,
        "require_agent_execute_permission",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v2", "model.alpha"),
    )

    def _save(execution, **_kwargs):
        saved_statuses.append(execution.status)

    monkeypatch.setattr(execution_service.executions_repo, "save_execution", _save)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {"prompt": "hello"},
        }
    )
    assert status == 201
    assert payload["execution"]["status"] == "succeeded"
    assert payload["execution"]["agent_version"] == "v2"
    assert saved_statuses == ["queued", "running", "succeeded"]


def test_execution_runtime_block_is_persisted(monkeypatch: pytest.MonkeyPatch):
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)

    def _blocked(**_kwargs):
        raise ExecutionBlockedError(
            code="EXEC_RUNTIME_PROFILE_BLOCKED",
            message="blocked",
            status_code=403,
        )

    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", _blocked)
    monkeypatch.setattr(
        execution_service.executions_repo,
        "save_execution",
        lambda execution, **_kwargs: captured.append(execution.to_payload()),
    )

    with pytest.raises(ExecutionBlockedError) as exc:
        execution_service.create_execution(
            {
                "agent_id": "agent.alpha",
                "requested_by_user_id": 123,
                "runtime_profile": "offline",
                "input": {},
            }
        )
    assert exc.value.code == "EXEC_RUNTIME_PROFILE_BLOCKED"
    assert captured[-1]["status"] == "blocked"
