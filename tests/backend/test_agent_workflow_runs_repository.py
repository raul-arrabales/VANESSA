from __future__ import annotations

from app.repositories import agent_workflow_runs


class _FakeResult:
    def fetchone(self) -> dict[str, object]:
        return {"id": "run-1"}


class _FakeConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, params: tuple[object, ...]) -> _FakeResult:
        self.executions.append((query, params))
        return _FakeResult()


def test_upsert_workflow_run_insert_query_matches_parameter_count(monkeypatch):
    connection = _FakeConnection()
    monkeypatch.setattr(agent_workflow_runs, "get_connection", lambda _db: connection)

    result = agent_workflow_runs.upsert_workflow_run(
        "ignored",
        owner_user_id=10,
        conversation_id="conversation-1",
        assistant_ref="agent.project.workflow-agent-1",
        status="awaiting_user_input",
        workflow_execution_mode="one_time",
        session_state="active",
        workflow_cycle=1,
        cycle_started_message_index=0,
        workflow_state={"status": "awaiting_user_input"},
    )

    insert_query, insert_params = connection.executions[0]
    assert "INSERT INTO agent_workflow_runs" in insert_query
    assert insert_query.count("%s") == len(insert_params)
    assert result == {"id": "run-1"}
