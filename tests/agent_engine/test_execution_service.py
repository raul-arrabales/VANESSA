from __future__ import annotations

import sys
from typing import Any
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from agent_engine.app.services import execution_service
from agent_engine.app.services.policy_runtime_gate import ExecutionBlockedError
from contract_fixtures import load_contract_fixture


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
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: {
                    "output_text": "model output",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
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
            "platform_runtime": {
                "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                },
            },
        }
    )
    assert status == 201
    assert payload["execution"]["status"] == "succeeded"
    assert payload["execution"]["agent_version"] == "v2"
    assert payload["execution"]["model_ref"] == "model.alpha"
    assert payload["execution"]["result"] == {
        "output_text": "model output",
        "tool_calls": [],
        "model_calls": [
            {
                "provider_slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "deployment_profile_slug": "local-default",
                "requested_model": "model.alpha",
                "status_code": 200,
            }
        ],
    }
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


def test_blocked_execution_contract_shape(monkeypatch: pytest.MonkeyPatch):
    golden = load_contract_fixture("agent_execution", "blocked_execution.json")["execution"]

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: golden["runtime_profile"])
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: (_ for _ in ()).throw(
            ExecutionBlockedError(
                code=golden["error"]["code"],
                message=golden["error"]["message"],
                status_code=403,
            )
        ),
    )

    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(
        execution_service.executions_repo,
        "save_execution",
        lambda execution, **_kwargs: captured.append(execution.to_payload()),
    )

    with pytest.raises(ExecutionBlockedError):
        execution_service.create_execution(
            {
                "agent_id": golden["agent_ref"],
                "requested_by_user_id": 123,
                "runtime_profile": golden["runtime_profile"],
                "input": {},
            }
        )

    assert set(captured[-1].keys()) == set(golden.keys())
    assert captured[-1]["status"] == "blocked"


def test_execution_without_prompt_or_messages_keeps_deterministic_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v1", None),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {},
        }
    )

    assert status == 201
    assert payload["execution"]["result"] == {
        "output_text": "Agent 'agent.alpha' executed in offline profile",
        "tool_calls": [],
        "model_calls": [],
    }


def test_execution_runtime_client_failures_map_to_existing_error_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v1", "model.alpha"),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FailingClient",
            (),
            {
                "chat_completion": lambda self, **_kwargs: (_ for _ in ()).throw(
                    execution_service.LlmRuntimeClientError(
                        code="runtime_unreachable",
                        message="upstream unavailable",
                        status_code=502,
                    )
                )
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    with pytest.raises(ExecutionBlockedError) as exc_info:
        execution_service.create_execution(
            {
                "agent_id": "agent.alpha",
                "requested_by_user_id": 123,
                "runtime_profile": "offline",
                "input": {"prompt": "hello"},
                "platform_runtime": {
                    "deployment_profile": {"slug": "local-default"},
                    "capabilities": {"llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"}},
                },
            }
        )

    assert exc_info.value.code == "EXEC_UPSTREAM_UNAVAILABLE"
