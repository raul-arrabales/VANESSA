from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from ..config import AuthConfig
from ..domain.conversation_actions import (
    ConversationActionState,
    ConversationActionType,
    find_conversation_action,
)
from ..domain.playgrounds import CHAT_PLAYGROUND_KIND
from ..infrastructure import playgrounds_repository
from ..repositories.agent_workflow_runs import get_workflow_run
from ..repositories.chat_conversations import MessageActionTransitionResult
from .playground_workflow_lifecycle import (
    WORKFLOW_EXECUTION_MODE_LOOP,
    WORKFLOW_SESSION_STATE_ACTIVE,
    build_workflow_runtime_state,
)

ACTION_EXECUTION_LEASE = timedelta(minutes=2)


def _is_expired(executing_at: Any) -> bool:
    try:
        parsed = datetime.fromisoformat(str(executing_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True
    return parsed <= datetime.now(tz=timezone.utc) - ACTION_EXECUTION_LEASE


def execute_playground_message_action(
    database_url: str,
    *,
    config: AuthConfig,
    owner_user_id: int,
    owner_role: str,
    session_id: str,
    message_id: str,
    action_id: str,
) -> dict[str, Any]:
    # Lazy import keeps the shared playground orchestration independent from the
    # action dispatcher while this service reuses its session/bootstrap APIs.
    from . import playgrounds_service as playgrounds

    row, messages = playgrounds._load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=CHAT_PLAYGROUND_KIND,
    )
    message = next((item for item in messages if str(item.get("id") or "") == message_id), None)
    metadata = message.get("metadata_json") if isinstance(message, dict) else None
    action = find_conversation_action(metadata, action_id)
    if message is None or str(message.get("role") or "") != "assistant" or action is None:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_not_found", "Conversation action not found")

    handlers: dict[str, Callable[..., dict[str, Any]]] = {
        ConversationActionType.START_WORKFLOW_CYCLE: _start_workflow_cycle,
    }
    handler = handlers.get(str(action.get("type") or ""))
    if handler is None:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_invalid", "Unsupported conversation action")
    return handler(
        database_url=database_url,
        config=config,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        session_id=session_id,
        message_id=message_id,
        action_id=action_id,
        action=action,
        session_row=row,
        playgrounds=playgrounds,
    )


def _start_workflow_cycle(*, database_url: str, config: AuthConfig, owner_user_id: int, owner_role: str,
                          session_id: str, message_id: str, action_id: str, action: dict[str, Any],
                          session_row: dict[str, Any], playgrounds: Any) -> dict[str, Any]:
    settings = playgrounds._workflow_assistant_settings(
        database_url, assistant_ref=playgrounds.string_or_none(session_row.get("assistant_ref"))
    )
    if not settings or settings.get("workflow_execution_mode") != WORKFLOW_EXECUTION_MODE_LOOP:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_invalid", "This action requires a loop workflow")
    assistant_ref = str(settings["assistant_ref"])
    workflow_run = get_workflow_run(
        database_url, owner_user_id=owner_user_id, conversation_id=session_id, assistant_ref=assistant_ref
    )
    runtime_state = build_workflow_runtime_state(
        workflow_run=workflow_run, workflow_execution_mode=settings.get("workflow_execution_mode")
    )
    completed_cycle = max(1, int(action.get("workflow_cycle") or 1))
    target_cycle = completed_cycle + 1

    # A previous process may have completed bootstrap before it could mark the
    # message action consumed. Reconcile that state without starting a duplicate.
    if runtime_state.workflow_cycle >= target_cycle:
        _transition(database_url, owner_user_id, session_id, message_id, action_id,
                    {ConversationActionState.EXECUTING, ConversationActionState.ENABLED}, ConversationActionState.CONSUMED)
        return playgrounds.get_playground_session_detail(
            database_url, owner_user_id=owner_user_id, session_id=session_id, playground_kind=CHAT_PLAYGROUND_KIND
        )
    if runtime_state.session_state != WORKFLOW_SESSION_STATE_ACTIVE:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_closed", "Workflow session is closed")
    if runtime_state.workflow_cycle != completed_cycle or not workflow_run or str(workflow_run.get("status") or "").lower() != "completed":
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_stale", "The workflow is not waiting to start another loop")

    state = str(action.get("state") or "")
    if state == ConversationActionState.CONSUMED:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_consumed", "This conversation action was already used")
    if state == ConversationActionState.EXECUTING and not _is_expired(action.get("executing_at")):
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_in_progress", "This conversation action is already running")
    expected = {ConversationActionState.ENABLED} if state == ConversationActionState.ENABLED else {ConversationActionState.EXECUTING}
    result = _transition(database_url, owner_user_id, session_id, message_id, action_id, expected, ConversationActionState.EXECUTING)
    if result == MessageActionTransitionResult.STATE_MISMATCH:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_in_progress", "This conversation action is already running")
    if result != MessageActionTransitionResult.UPDATED:
        raise playgrounds.PlaygroundSessionValidationError("conversation_action_not_found", "Conversation action not found")
    try:
        playgrounds._maybe_bootstrap_workflow_session(
            database_url, config=config, owner_user_id=owner_user_id, owner_role=owner_role,
            session_row=session_row, workflow_execution_mode=WORKFLOW_EXECUTION_MODE_LOOP, workflow_cycle=target_cycle,
        )
    except Exception:
        _transition(database_url, owner_user_id, session_id, message_id, action_id,
                    {ConversationActionState.EXECUTING}, ConversationActionState.ENABLED)
        raise
    _transition(database_url, owner_user_id, session_id, message_id, action_id,
                {ConversationActionState.EXECUTING}, ConversationActionState.CONSUMED)
    return playgrounds.get_playground_session_detail(
        database_url, owner_user_id=owner_user_id, session_id=session_id, playground_kind=CHAT_PLAYGROUND_KIND
    )


def _transition(database_url: str, owner_user_id: int, session_id: str, message_id: str,
                action_id: str, expected_states: set[str], next_state: str) -> MessageActionTransitionResult:
    return playgrounds_repository.transition_message_action(
        database_url, owner_user_id=owner_user_id, conversation_id=session_id,
        message_id=message_id, action_id=action_id, expected_states=expected_states, next_state=next_state,
    )
