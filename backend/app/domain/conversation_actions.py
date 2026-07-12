from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict
from uuid import uuid4


class ConversationActionType(StrEnum):
    START_WORKFLOW_CYCLE = "start_workflow_cycle"


class ConversationActionState(StrEnum):
    ENABLED = "enabled"
    EXECUTING = "executing"
    CONSUMED = "consumed"
    DISABLED = "disabled"


class ConversationActionEmphasis(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class ConversationAction(TypedDict, total=False):
    id: str
    type: str
    label_key: str
    label: str
    emphasis: str
    state: str
    executing_at: str
    consumed_at: str
    workflow_cycle: int


def build_start_workflow_cycle_action(*, workflow_cycle: int) -> ConversationAction:
    return {
        "id": str(uuid4()),
        "type": ConversationActionType.START_WORKFLOW_CYCLE,
        "label_key": "start_next_loop",
        "label": "Start next loop",
        "emphasis": ConversationActionEmphasis.PRIMARY,
        "state": ConversationActionState.ENABLED,
        "workflow_cycle": max(1, int(workflow_cycle)),
    }


def find_conversation_action(metadata: Any, action_id: str) -> ConversationAction | None:
    actions = metadata.get("actions") if isinstance(metadata, dict) else None
    if not isinstance(actions, list):
        return None
    return next(
        (
            action
            for action in actions
            if isinstance(action, dict) and str(action.get("id") or "") == action_id
        ),
        None,
    )
