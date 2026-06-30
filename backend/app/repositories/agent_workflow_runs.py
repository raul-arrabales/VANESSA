from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import psycopg

from ..db import get_connection


def get_workflow_run(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    assistant_ref: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                id,
                conversation_id,
                owner_user_id,
                assistant_ref,
                status,
                workflow_execution_mode,
                session_state,
                workflow_cycle,
                cycle_started_message_index,
                workflow_state,
                created_at,
                updated_at
            FROM agent_workflow_runs
            WHERE owner_user_id = %s AND conversation_id = %s AND assistant_ref = %s
            """,
            (owner_user_id, conversation_id, assistant_ref),
        ).fetchone()
    return dict(row) if row else None


def upsert_workflow_run(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    assistant_ref: str,
    status: str,
    workflow_execution_mode: str,
    session_state: str,
    workflow_cycle: int,
    cycle_started_message_index: int,
    workflow_state: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    run_id = str(uuid4())
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO agent_workflow_runs (
                id,
                conversation_id,
                owner_user_id,
                assistant_ref,
                status,
                workflow_execution_mode,
                session_state,
                workflow_cycle,
                cycle_started_message_index,
                workflow_state,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (conversation_id, assistant_ref)
            DO UPDATE SET
                status = EXCLUDED.status,
                workflow_execution_mode = EXCLUDED.workflow_execution_mode,
                session_state = EXCLUDED.session_state,
                workflow_cycle = EXCLUDED.workflow_cycle,
                cycle_started_message_index = EXCLUDED.cycle_started_message_index,
                workflow_state = EXCLUDED.workflow_state,
                updated_at = EXCLUDED.updated_at
            RETURNING
                id,
                conversation_id,
                owner_user_id,
                assistant_ref,
                status,
                workflow_execution_mode,
                session_state,
                workflow_cycle,
                cycle_started_message_index,
                workflow_state,
                created_at,
                updated_at
            """,
            (
                run_id,
                conversation_id,
                owner_user_id,
                assistant_ref,
                status,
                workflow_execution_mode,
                session_state,
                workflow_cycle,
                cycle_started_message_index,
                psycopg.types.json.Jsonb(workflow_state),
                now,
                now,
            ),
        ).fetchone()
    return dict(row or {})
