from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.repositories import modelops


class _FakeResult:
    def __init__(self, *, one=None, many=None):
        self._one = one
        self._many = list(many or [])

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._many)


def test_list_models_for_superadmin_applies_active_and_capability_filters(monkeypatch):
    captured: dict[str, object] = {}
    expected_rows = [
        {
            "model_id": "embed-active",
            "name": "Embedding Active",
            "task_key": "embeddings",
            "lifecycle_state": "active",
        }
    ]

    class _FakeConnection:
        def execute(self, query, params=None):
            captured["query"] = str(query)
            captured["params"] = params
            return _FakeResult(many=expected_rows)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(modelops, "get_connection", _fake_get_connection)

    rows = modelops.list_models_for_actor(
        "postgresql://ignored",
        actor_user_id=1,
        actor_role="superadmin",
        runtime_profile="online",
        require_active=True,
        capability_key="embeddings",
    )

    assert rows == expected_rows
    assert "m.lifecycle_state = 'active'" in captured["query"]
    assert "m.is_validation_current = TRUE" in captured["query"]
    assert "m.last_validation_status = 'success'" in captured["query"]
    assert "c.id = m.credential_id AND c.is_active = TRUE" in captured["query"]
    assert "m.task_key = 'embeddings'" in captured["query"]
    assert "user_role_cte" not in captured["query"]
    assert captured["params"] == ("online",)


def test_list_models_for_user_applies_visibility_assignment_and_offline_filters(monkeypatch):
    captured: dict[str, object] = {}
    expected_rows = [
        {
            "model_id": "allowed-model",
            "name": "Allowed Model",
            "visibility_scope": "user",
            "task_key": "llm",
        }
    ]

    class _FakeConnection:
        def execute(self, query, params=None):
            captured["query"] = str(query)
            captured["params"] = params
            return _FakeResult(many=expected_rows)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(modelops, "get_connection", _fake_get_connection)

    rows = modelops.list_models_for_actor(
        "postgresql://ignored",
        actor_user_id=42,
        actor_role="user",
        runtime_profile="offline",
        require_active=False,
        capability_key="llm_inference",
    )

    assert rows == expected_rows
    assert "WITH user_role_cte AS (" in captured["query"]
    assert "user_groups_cte AS (" in captured["query"]
    assert "assigned_models AS (" in captured["query"]
    assert "(m.owner_type = 'user' AND m.owner_user_id = %s)" in captured["query"]
    assert "m.visibility_scope = 'platform'" in captured["query"]
    assert "(m.visibility_scope IN ('user', 'group') AND a.model_id IS NOT NULL)" in captured["query"]
    assert "%s <> 'offline'" in captured["query"]
    assert "m.runtime_mode_policy = 'online_offline'" in captured["query"]
    assert "m.hosting_kind = 'local'" in captured["query"]
    assert "m.availability = 'offline_ready'" in captured["query"]
    assert "m.task_key = 'llm'" in captured["query"]
    assert captured["params"] == (42, 42, 42, 42, "offline")


def test_get_model_selects_artifact_and_dependency_subqueries(monkeypatch):
    captured: dict[str, object] = {}
    expected_row = {
        "model_id": "model-1",
        "artifact": {"storage_path": "/models/model-1"},
        "dependencies": [{"dependency_kind": "provider", "dependency_key": "provider"}],
    }

    class _FakeConnection:
        def execute(self, query, params=None):
            captured["query"] = str(query)
            captured["params"] = params
            return _FakeResult(one=expected_row)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(modelops, "get_connection", _fake_get_connection)

    row = modelops.get_model("postgresql://ignored", "model-1")

    assert row == expected_row
    assert "FROM model_artifacts ma" in captured["query"]
    assert "FROM model_runtime_dependencies d" in captured["query"]
    assert "WHERE m.model_id = %s" in captured["query"]
    assert captured["params"] == ("model-1",)


def test_list_model_picker_rows_for_user_uses_lightweight_projection(monkeypatch):
    captured: dict[str, object] = {}
    expected_rows = [
        {
            "model_id": "allowed-model",
            "name": "Allowed Model",
            "task_key": "llm",
        }
    ]

    class _FakeConnection:
        def execute(self, query, params=None):
            captured["query"] = str(query)
            captured["params"] = params
            return _FakeResult(many=expected_rows)

    @contextmanager
    def _fake_get_connection(_database_url: str) -> Iterator[_FakeConnection]:
        yield _FakeConnection()

    monkeypatch.setattr(modelops, "get_connection", _fake_get_connection)

    rows = modelops.list_model_picker_rows_for_actor(
        "postgresql://ignored",
        actor_user_id=42,
        actor_role="user",
        runtime_profile="online",
        require_active=True,
        capability_key="llm_inference",
    )

    assert rows == expected_rows
    assert "SELECT DISTINCT" in captured["query"]
    assert "m.model_id" in captured["query"]
    assert "m.name" in captured["query"]
    assert "m.task_key" in captured["query"]
    assert "FROM model_artifacts ma" not in captured["query"]
    assert "FROM model_runtime_dependencies d" not in captured["query"]
    assert captured["params"] == (42, 42, 42, 42, "online")
