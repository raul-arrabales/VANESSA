from __future__ import annotations

import json
import threading
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

from ..schemas.agent_executions import AgentExecutionRecord
try:  # pragma: no cover - import path varies by invocation style
    from ..config import get_config
except ImportError:  # pragma: no cover
    from agent_engine.app.config import get_config

_LOCK = threading.Lock()
_DB_READY = False
_MEMORY_EXECUTIONS: dict[str, dict[str, Any]] = {}


def _database_url() -> str:
    return get_config().database_url


def _db_available() -> bool:
    return bool(psycopg is not None and dict_row is not None and _database_url())


def ensure_schema() -> None:
    global _DB_READY
    if _DB_READY or not _db_available():
        return

    try:
        with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    runtime_profile TEXT NOT NULL,
                    requested_by_user_id BIGINT,
                    input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        _DB_READY = True
    except Exception:
        _DB_READY = False


def _encode_result_json(execution: AgentExecutionRecord) -> dict[str, Any]:
    return {
        "execution_payload": execution.to_payload(),
        "result": execution.result if execution.result is not None else {},
        "error": execution.error,
        "agent_version": execution.agent_version,
        "model_ref": execution.model_ref,
        "started_at": execution.started_at,
        "finished_at": execution.finished_at,
    }


def _row_to_execution(row: dict[str, Any]) -> AgentExecutionRecord | None:
    result_json = row.get("result_json") if isinstance(row.get("result_json"), dict) else {}
    execution_payload = result_json.get("execution_payload")
    if isinstance(execution_payload, dict):
        try:
            return AgentExecutionRecord.from_payload(execution_payload)
        except ValueError:
            pass

    return AgentExecutionRecord.from_payload(
        {
            "id": row["id"],
            "status": row.get("status", "failed"),
            "agent_ref": row.get("agent_id", ""),
            "agent_version": str(result_json.get("agent_version", "v1") or "v1"),
            "model_ref": result_json.get("model_ref"),
            "runtime_profile": row.get("runtime_profile", "offline"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else row.get("updated_at").isoformat(),
            "started_at": result_json.get("started_at"),
            "finished_at": result_json.get("finished_at"),
            "result": result_json.get("result") if isinstance(result_json.get("result"), dict) else {},
            "error": result_json.get("error") if isinstance(result_json.get("error"), dict) else None,
        }
    )


def save_execution(
    execution: AgentExecutionRecord,
    *,
    requested_by_user_id: int | None = None,
    input_payload: dict[str, Any] | None = None,
) -> None:
    with _LOCK:
        _MEMORY_EXECUTIONS[execution.id] = {
            "execution_payload": execution.to_payload(),
            "requested_by_user_id": requested_by_user_id,
            "input_payload": input_payload if isinstance(input_payload, dict) else {},
        }

    ensure_schema()
    if not _DB_READY:
        return

    try:
        with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
            connection.execute(
                """
                INSERT INTO agent_executions (
                    id,
                    agent_id,
                    status,
                    runtime_profile,
                    requested_by_user_id,
                    input_json,
                    result_json,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::timestamptz, NOW())
                ON CONFLICT (id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    runtime_profile = EXCLUDED.runtime_profile,
                    requested_by_user_id = EXCLUDED.requested_by_user_id,
                    input_json = EXCLUDED.input_json,
                    result_json = EXCLUDED.result_json,
                    updated_at = NOW()
                """,
                (
                    execution.id,
                    execution.agent_ref,
                    execution.status,
                    execution.runtime_profile,
                    requested_by_user_id,
                    json.dumps(input_payload if isinstance(input_payload, dict) else {}),
                    json.dumps(_encode_result_json(execution)),
                    execution.created_at,
                ),
            )
    except Exception:
        return


def get_execution(execution_id: str) -> AgentExecutionRecord | None:
    with _LOCK:
        memory = _MEMORY_EXECUTIONS.get(execution_id)
        if memory is not None:
            payload = memory.get("execution_payload")
            if isinstance(payload, dict):
                return AgentExecutionRecord.from_payload(payload)

    ensure_schema()
    if not _DB_READY:
        return None

    try:
        with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
            row = connection.execute(
                """
                SELECT id, agent_id, status, runtime_profile, result_json, created_at, updated_at
                FROM agent_executions
                WHERE id = %s
                """,
                (execution_id,),
            ).fetchone()
            if row is None:
                return None
            return _row_to_execution(dict(row))
    except Exception:
        return None
