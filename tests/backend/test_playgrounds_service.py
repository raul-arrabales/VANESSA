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
