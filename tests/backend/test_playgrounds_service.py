from __future__ import annotations

from app.application import playgrounds_service
from app.config import AuthConfig


def test_get_playground_options_returns_runtime_models_and_bound_knowledge_bases(monkeypatch):
    config = AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        model_credentials_encryption_key="test-credential-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
    )

    monkeypatch.setattr(
        playgrounds_service,
        "list_models",
        lambda *_args, **_kwargs: [
            {"id": "safe-small", "name": "Safe Small", "task_key": "llm"},
            {"id": "safe-large", "name": "Safe Large", "task_key": "llm"},
        ],
    )
    monkeypatch.setattr(
        playgrounds_service,
        "list_knowledge_chat_knowledge_bases",
        lambda **_kwargs: (
            {
                "knowledge_bases": [{"id": "kb-primary", "display_name": "Product Docs", "index_name": "kb_product_docs", "is_default": True}],
                "default_knowledge_base_id": "kb-primary",
                "selection_required": False,
                "configuration_message": None,
            },
            200,
        ),
    )

    payload = playgrounds_service.get_playground_options(
        "postgresql://ignored",
        config=config,
        actor_user_id=10,
        actor_role="user",
    )

    assert payload["assistants"][0]["assistant_ref"] == "assistant.playground.chat"
    assert {assistant["assistant_ref"] for assistant in payload["assistants"]} >= {
        "assistant.playground.chat",
        "assistant.vanessa.core",
        "agent.knowledge_chat",
    }
    assert payload["models"][1]["display_name"] == "Safe Large"
    assert payload["default_knowledge_base_id"] == "kb-primary"


def test_send_playground_message_requires_knowledge_binding_for_knowledge_sessions(monkeypatch):
    def _get_session(_database_url: str, *, owner_user_id: int, conversation_id: str, conversation_kind: str):
        if conversation_kind == "knowledge":
            return {
                "id": conversation_id,
                "conversation_kind": "knowledge",
                "title": "Knowledge session",
                "title_source": "auto",
                "model_id": "safe-small",
                "knowledge_base_id": None,
                "assistant_ref": "agent.knowledge_chat",
            }
        return None

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "get_session", _get_session)
    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "list_messages", lambda *_args, **_kwargs: [])

    config = AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        model_credentials_encryption_key="test-credential-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
    )

    try:
        playgrounds_service.send_playground_message(
            "postgresql://ignored",
            config=config,
            request_id="req-1",
            owner_user_id=10,
            owner_role="user",
            session_id="sess-1",
            prompt="hello",
        )
    except playgrounds_service.PlaygroundSessionValidationError as exc:
        assert exc.code == "knowledge_base_required"
        assert "knowledge_base_id" in exc.message
    else:  # pragma: no cover
        raise AssertionError("Expected knowledge playground validation error")


def test_send_playground_message_runs_chat_execution_and_auto_titles_first_message(monkeypatch):
    captured: dict[str, object] = {}

    def _get_session(_database_url: str, *, owner_user_id: int, conversation_id: str, conversation_kind: str):
        if conversation_kind == "plain":
            return {
                "id": conversation_id,
                "conversation_kind": "plain",
                "title": "New chat session",
                "title_source": "auto",
                "model_id": "safe-small",
                "knowledge_base_id": None,
                "assistant_ref": "assistant.playground.chat",
            }
        return None

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "get_session", _get_session)
    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "list_messages", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playgrounds_service,
        "chat_completion_with_allowed_model",
        lambda **_kwargs: (
            {
                "output": [
                    {
                        "content": [{"type": "text", "text": "assistant reply"}],
                    }
                ]
            },
            200,
        ),
    )

    def _append_message_pair(_database_url: str, **kwargs):
        captured.update(kwargs)
        return {
            "conversation": {"id": kwargs["conversation_id"]},
            "messages": [
                {"id": "msg-user", "role": "user", "content": kwargs["user_content"], "metadata_json": {}, "created_at": "2026-03-18T11:00:00+00:00"},
                {"id": "msg-assistant", "role": "assistant", "content": kwargs["assistant_content"], "metadata_json": {}, "created_at": "2026-03-18T11:00:01+00:00"},
            ],
        }

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "append_message_pair", _append_message_pair)
    monkeypatch.setattr(
        playgrounds_service,
        "get_playground_session_detail",
        lambda *_args, **_kwargs: {
            "id": "sess-1",
            "playground_kind": "chat",
            "messages": [],
        },
    )

    config = AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        model_credentials_encryption_key="test-credential-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
    )

    payload = playgrounds_service.send_playground_message(
        "postgresql://ignored",
        config=config,
        request_id="req-chat",
        owner_user_id=10,
        owner_role="user",
        session_id="sess-1",
        prompt="hello from chat",
    )

    assert payload["output"] == "assistant reply"
    assert captured["conversation_title"] == "hello from chat"
    assert captured["title_source"] == "auto"
    assert captured["assistant_metadata"] is None
    assert payload["messages"][1]["content"] == "assistant reply"


def test_send_playground_message_persists_structured_knowledge_metadata(monkeypatch):
    captured: dict[str, object] = {}

    def _get_session(_database_url: str, *, owner_user_id: int, conversation_id: str, conversation_kind: str):
        if conversation_kind == "knowledge":
            return {
                "id": conversation_id,
                "conversation_kind": "knowledge",
                "title": "Knowledge session",
                "title_source": "auto",
                "model_id": "safe-small",
                "knowledge_base_id": "kb-primary",
                "assistant_ref": "agent.knowledge_chat",
            }
        return None

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "get_session", _get_session)
    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "list_messages", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playgrounds_service,
        "execute_knowledge_request",
        lambda **_kwargs: playgrounds_service.PlaygroundExecutionResult(
            output="knowledge answer",
            response={"id": "exec-1"},
            sources=[{"id": "doc-1", "title": "Architecture Overview"}],
            retrieval={"index": "kb_product_docs", "result_count": 1},
            knowledge_base_id="kb-primary",
        ),
    )

    def _append_message_pair(_database_url: str, **kwargs):
        captured.update(kwargs)
        return {
            "conversation": {"id": kwargs["conversation_id"]},
            "messages": [
                {"id": "msg-user", "role": "user", "content": kwargs["user_content"], "metadata_json": {}, "created_at": "2026-03-18T11:00:00+00:00"},
                {"id": "msg-assistant", "role": "assistant", "content": kwargs["assistant_content"], "metadata_json": kwargs["assistant_metadata"], "created_at": "2026-03-18T11:00:01+00:00"},
            ],
        }

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "append_message_pair", _append_message_pair)
    monkeypatch.setattr(
        playgrounds_service,
        "get_playground_session_detail",
        lambda *_args, **_kwargs: {
            "id": "sess-knowledge",
            "playground_kind": "knowledge",
            "messages": [],
        },
    )

    config = AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        model_credentials_encryption_key="test-credential-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
    )

    payload = playgrounds_service.send_playground_message(
        "postgresql://ignored",
        config=config,
        request_id="req-knowledge",
        owner_user_id=10,
        owner_role="user",
        session_id="sess-knowledge",
        prompt="hello knowledge",
    )

    assert payload["output"] == "knowledge answer"
    assert captured["assistant_metadata"] == {
        "response": {"id": "exec-1"},
        "sources": [{"id": "doc-1", "title": "Architecture Overview"}],
        "retrieval": {"index": "kb_product_docs", "result_count": 1},
        "knowledge_base_id": "kb-primary",
    }
    assert payload["retrieval"] == {"index": "kb_product_docs", "result_count": 1}


def test_update_playground_session_preserves_unchanged_fields_when_binding_kb(monkeypatch):
    session_row = {
        "id": "sess-knowledge",
        "conversation_kind": "knowledge",
        "title": "Knowledge session",
        "title_source": "auto",
        "model_id": "safe-small",
        "knowledge_base_id": None,
        "assistant_ref": "agent.knowledge_chat",
        "created_at": "2026-03-18T11:00:00+00:00",
        "updated_at": "2026-03-18T11:00:00+00:00",
        "message_count": 0,
    }

    monkeypatch.setattr(
        playgrounds_service,
        "_require_session",
        lambda *_args, **_kwargs: session_row,
    )

    def _update_session(_database_url: str, **kwargs):
        assert kwargs["title"] is playgrounds_service.SESSION_UNSET
        assert kwargs["title_source"] is playgrounds_service.SESSION_UNSET
        assert kwargs["assistant_ref"] is playgrounds_service.SESSION_UNSET
        assert kwargs["model_id"] is playgrounds_service.SESSION_UNSET
        assert kwargs["knowledge_base_id"] == "kb-primary"
        return {
            **session_row,
            "knowledge_base_id": "kb-primary",
        }

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "update_session", _update_session)

    updated = playgrounds_service.update_playground_session(
        "postgresql://ignored",
        owner_user_id=10,
        session_id="sess-knowledge",
        payload={"knowledge_binding": {"knowledge_base_id": "kb-primary"}},
    )

    assert updated["knowledge_binding"]["knowledge_base_id"] == "kb-primary"
    assert updated["title"] == "Knowledge session"
    assert updated["model_selection"]["model_id"] == "safe-small"
