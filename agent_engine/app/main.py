from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional in constrained envs
    psycopg = None
    dict_row = None

_EXECUTIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_DB_READY = False


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def _db_available() -> bool:
    return bool(psycopg is not None and dict_row is not None and _database_url())


def _ensure_db_schema() -> None:
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


def _persist_execution(execution: dict[str, Any]) -> None:
    _ensure_db_schema()
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
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::timestamptz, %s::timestamptz)
                ON CONFLICT (id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    runtime_profile = EXCLUDED.runtime_profile,
                    requested_by_user_id = EXCLUDED.requested_by_user_id,
                    input_json = EXCLUDED.input_json,
                    result_json = EXCLUDED.result_json,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    execution["id"],
                    execution["agent_id"],
                    execution["status"],
                    execution["runtime_profile"],
                    execution.get("requested_by_user_id"),
                    json.dumps(execution.get("input", {})),
                    json.dumps(execution.get("result", {})),
                    execution["created_at"],
                    execution["updated_at"],
                ),
            )
    except Exception:
        # Continue serving via in-memory fallback.
        pass


def _load_execution(execution_id: str) -> dict[str, Any] | None:
    _ensure_db_schema()
    if _DB_READY:
        try:
            with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT id, agent_id, status, runtime_profile, requested_by_user_id,
                           input_json, result_json, created_at, updated_at
                    FROM agent_executions
                    WHERE id = %s
                    """,
                    (execution_id,),
                ).fetchone()
                if row:
                    return {
                        "id": row["id"],
                        "agent_id": row["agent_id"],
                        "status": row["status"],
                        "runtime_profile": row["runtime_profile"],
                        "requested_by_user_id": row.get("requested_by_user_id"),
                        "input": row.get("input_json") if isinstance(row.get("input_json"), dict) else {},
                        "result": row.get("result_json") if isinstance(row.get("result_json"), dict) else {},
                        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
                    }
        except Exception:
            pass

    with _LOCK:
        return _EXECUTIONS.get(execution_id)


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSAAgentEngine/0.2"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "service": "agent_engine", "db_ready": _DB_READY})
            return

        if parsed.path.startswith("/v1/agent-executions/"):
            execution_id = parsed.path.split("/")[-1].strip()
            if not execution_id:
                self._send_json(400, {"error": "invalid_execution_id", "message": "execution_id is required"})
                return

            execution = _load_execution(execution_id)
            if execution is None:
                self._send_json(404, {"error": "execution_not_found", "message": "Execution not found"})
                return
            self._send_json(200, {"execution": execution})
            return

        self._send_json(404, {"error": "not_found", "message": "Route not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/v1/agent-executions":
            self._send_json(404, {"error": "not_found", "message": "Route not found"})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return

        agent_id = str(payload.get("agent_id", "")).strip()
        if not agent_id:
            self._send_json(400, {"error": "invalid_agent_id", "message": "agent_id is required"})
            return

        runtime_profile = str(payload.get("runtime_profile", "offline")).strip().lower() or "offline"
        execution_id = str(uuid4())
        now = _iso_now()

        output_text = f"Agent '{agent_id}' executed in {runtime_profile} profile"
        execution = {
            "id": execution_id,
            "agent_id": agent_id,
            "status": "succeeded",
            "runtime_profile": runtime_profile,
            "requested_by_user_id": payload.get("requested_by_user_id"),
            "input": payload.get("input") if isinstance(payload.get("input"), dict) else {},
            "result": {
                "output_text": output_text,
                "tool_calls": [],
                "model_calls": [],
            },
            "created_at": now,
            "updated_at": now,
        }

        with _LOCK:
            _EXECUTIONS[execution_id] = execution

        _persist_execution(execution)
        self._send_json(201, {"execution": execution})


if __name__ == "__main__":
    _ensure_db_schema()
    server = HTTPServer(("0.0.0.0", 7000), Handler)
    server.serve_forever()
