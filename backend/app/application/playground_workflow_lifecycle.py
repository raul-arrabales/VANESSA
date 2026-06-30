from __future__ import annotations

from dataclasses import dataclass
from typing import Any

WORKFLOW_EXECUTION_MODE_ONE_TIME = "one_time"
WORKFLOW_EXECUTION_MODE_LOOP = "loop"
WORKFLOW_SESSION_STATE_ACTIVE = "active"
WORKFLOW_SESSION_STATE_CLOSED = "closed"


@dataclass(frozen=True)
class WorkflowRuntimeState:
    execution_mode: str
    session_state: str
    workflow_cycle: int
    cycle_started_message_index: int


@dataclass(frozen=True)
class WorkflowLifecycleOutcome:
    should_bootstrap_next_cycle: bool
    bootstrap_workflow_cycle: int | None
    persisted_session_state: str | None
    persisted_workflow_cycle: int | None
    cycle_started_message_index: int


def normalize_workflow_execution_mode(value: Any) -> str:
    normalized = str(value or WORKFLOW_EXECUTION_MODE_ONE_TIME).strip().lower() or WORKFLOW_EXECUTION_MODE_ONE_TIME
    return normalized if normalized in {WORKFLOW_EXECUTION_MODE_ONE_TIME, WORKFLOW_EXECUTION_MODE_LOOP} else WORKFLOW_EXECUTION_MODE_ONE_TIME


def normalize_workflow_session_state(value: Any) -> str:
    normalized = str(value or WORKFLOW_SESSION_STATE_ACTIVE).strip().lower() or WORKFLOW_SESSION_STATE_ACTIVE
    return normalized if normalized in {WORKFLOW_SESSION_STATE_ACTIVE, WORKFLOW_SESSION_STATE_CLOSED} else WORKFLOW_SESSION_STATE_ACTIVE


def is_closed_workflow_session(value: Any) -> bool:
    return normalize_workflow_session_state(value) == WORKFLOW_SESSION_STATE_CLOSED


def build_workflow_runtime_state(
    *,
    workflow_run: dict[str, Any] | None,
    workflow_execution_mode: Any,
) -> WorkflowRuntimeState:
    run = workflow_run if isinstance(workflow_run, dict) else {}
    return WorkflowRuntimeState(
        execution_mode=normalize_workflow_execution_mode(workflow_execution_mode),
        session_state=normalize_workflow_session_state(run.get("session_state")),
        workflow_cycle=max(1, int(run.get("workflow_cycle", 1) or 1)),
        cycle_started_message_index=max(0, int(run.get("cycle_started_message_index", 0) or 0)),
    )


def filter_history_for_current_workflow_cycle(
    history_messages: list[dict[str, Any]],
    *,
    cycle_started_message_index: int,
) -> list[dict[str, Any]]:
    boundary = max(0, int(cycle_started_message_index or 0))
    return [
        item
        for item in history_messages
        if int(item.get("message_index", 0) or 0) >= boundary
    ]


def resolve_workflow_lifecycle_outcome(
    *,
    workflow_execution_mode: Any,
    workflow_status: Any,
    workflow_cycle: Any,
    cycle_started_message_index: Any,
) -> WorkflowLifecycleOutcome:
    normalized_execution_mode = normalize_workflow_execution_mode(workflow_execution_mode)
    normalized_workflow_cycle = max(1, int(workflow_cycle or 1))
    normalized_cycle_boundary = max(0, int(cycle_started_message_index or 0))
    completed = str(workflow_status or "").strip().lower() == "completed"
    if normalized_execution_mode == WORKFLOW_EXECUTION_MODE_LOOP and completed:
        return WorkflowLifecycleOutcome(
            should_bootstrap_next_cycle=True,
            bootstrap_workflow_cycle=normalized_workflow_cycle + 1,
            persisted_session_state=None,
            persisted_workflow_cycle=None,
            cycle_started_message_index=normalized_cycle_boundary,
        )
    return WorkflowLifecycleOutcome(
        should_bootstrap_next_cycle=False,
        bootstrap_workflow_cycle=None,
        persisted_session_state=(
            WORKFLOW_SESSION_STATE_CLOSED
            if normalized_execution_mode == WORKFLOW_EXECUTION_MODE_ONE_TIME and completed
            else WORKFLOW_SESSION_STATE_ACTIVE
        ),
        persisted_workflow_cycle=normalized_workflow_cycle,
        cycle_started_message_index=normalized_cycle_boundary,
    )
