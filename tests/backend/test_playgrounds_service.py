from __future__ import annotations

from app.application import playground_execution, playgrounds_service
from app.config import AuthConfig


def test_build_context_messages_keeps_stable_prompt_prefix_ahead_of_recent_history():
    history = [
        {"role": "system", "content": "stable instructions"},
        *[
            {"role": "user" if index % 2 else "assistant", "content": f"turn {index}"}
            for index in range(20)
        ],
    ]

    messages = playground_execution.build_context_messages(history, prompt="latest question")

    assert messages[0] == {"role": "system", "content": [{"type": "text", "text": "stable instructions"}]}
    assert messages[-1] == {"role": "user", "content": [{"type": "text", "text": "latest question"}]}
    assert len(messages) == playground_execution.MAX_CONTEXT_MESSAGES + 2


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
        "list_model_picker_options",
        lambda *_args, **_kwargs: [
            {"id": "safe-small", "display_name": "Safe Small", "task_key": "llm"},
            {"id": "safe-large", "display_name": "Safe Large", "task_key": "llm"},
        ],
    )
    monkeypatch.setattr(
        playgrounds_service,
        "get_active_platform_runtime",
        lambda *_args, **_kwargs: {
            "capabilities": {
                "llm_inference": {
                    "resources": [
                        {"id": "safe-small", "display_name": "Safe Small"},
                        {"id": "safe-large", "display_name": "Safe Large"},
                    ]
                }
            }
        },
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


def test_get_playground_model_options_returns_lightweight_models_and_filtered_assistants(monkeypatch):
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
        "list_model_picker_options",
        lambda *_args, **_kwargs: [
            {"id": "safe-small", "display_name": "Safe Small", "task_key": "llm"},
            {"id": "safe-large", "display_name": "Safe Large", "task_key": "llm"},
        ],
    )
    monkeypatch.setattr(
        playgrounds_service,
        "get_active_platform_runtime",
        lambda *_args, **_kwargs: {
            "capabilities": {
                "llm_inference": {
                    "resources": [
                        {"id": "safe-small", "display_name": "Safe Small"},
                        {"id": "safe-large", "display_name": "Safe Large"},
                    ]
                }
            }
        },
    )
    monkeypatch.setattr(
        playgrounds_service,
        "list_knowledge_chat_knowledge_bases",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("knowledge bases should not be loaded")),
    )

    payload = playgrounds_service.get_playground_model_options(
        "postgresql://ignored",
        config=config,
        actor_user_id=10,
        actor_role="user",
        playground_kind="knowledge",
    )

    assert payload["models"][0]["display_name"] == "Safe Small"
    assert {assistant["assistant_ref"] for assistant in payload["assistants"]} == {"agent.knowledge_chat"}


def test_get_playground_model_options_excludes_models_not_bound_to_active_deployment(monkeypatch):
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
        "list_model_picker_options",
        lambda *_args, **_kwargs: [
            {"id": "Qwen--Qwen2.5-0.5B-Instruct", "display_name": "Qwen2.5-0.5B-Instruct", "task_key": "llm"},
            {"id": "openai-gpt-5-nano", "display_name": "gpt-5-nano", "task_key": "llm"},
        ],
    )
    monkeypatch.setattr(
        playgrounds_service,
        "get_active_platform_runtime",
        lambda *_args, **_kwargs: {
            "capabilities": {
                "llm_inference": {
                    "resources": [
                        {
                            "id": "openai-gpt-5-nano",
                            "display_name": "gpt-5-nano",
                            "provider_resource_id": "gpt-5-nano",
                        }
                    ]
                }
            }
        },
    )

    chat_payload = playgrounds_service.get_playground_model_options(
        "postgresql://ignored",
        config=config,
        actor_user_id=10,
        actor_role="user",
        playground_kind="chat",
    )
    knowledge_payload = playgrounds_service.get_playground_model_options(
        "postgresql://ignored",
        config=config,
        actor_user_id=10,
        actor_role="user",
        playground_kind="knowledge",
    )

    assert chat_payload["models"] == [{"id": "openai-gpt-5-nano", "display_name": "gpt-5-nano", "task_key": "llm"}]
    assert knowledge_payload["models"] == [{"id": "openai-gpt-5-nano", "display_name": "gpt-5-nano", "task_key": "llm"}]


def test_get_playground_knowledge_base_options_returns_fallback_configuration_message(monkeypatch):
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

    def _raise_control_plane_error(**_kwargs):
        raise playgrounds_service.PlatformControlPlaneError(
            "knowledge_base_not_configured",
            "Knowledge bases are not configured.",
            status_code=409,
        )

    monkeypatch.setattr(playgrounds_service, "list_knowledge_chat_knowledge_bases", _raise_control_plane_error)

    payload = playgrounds_service.get_playground_knowledge_base_options(
        "postgresql://ignored",
        config=config,
    )

    assert payload == {
        "knowledge_bases": [],
        "default_knowledge_base_id": None,
        "selection_required": False,
        "configuration_message": "Knowledge bases are not configured.",
    }


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
            sources=[
                {
                    "id": "doc-1",
                    "title": "Architecture Overview",
                    "file_url": "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
                }
            ],
            references=[
                {
                    "id": "ref-1",
                    "citation_label": "[1]",
                    "title": "Architecture Overview",
                    "pages": [4],
                    "file_url": "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
                }
            ],
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
        "sources": [
            {
                "id": "doc-1",
                "title": "Architecture Overview",
                "file_url": "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
            }
        ],
        "references": [
            {
                "id": "ref-1",
                "citation_label": "[1]",
                "title": "Architecture Overview",
                "pages": [4],
                "file_url": "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
            }
        ],
        "retrieval": {"index": "kb_product_docs", "result_count": 1},
        "knowledge_base_id": "kb-primary",
    }
    assert payload["retrieval"] == {"index": "kb_product_docs", "result_count": 1}
    assert payload["references"] == [
        {
            "id": "ref-1",
            "citation_label": "[1]",
            "title": "Architecture Overview",
            "pages": [4],
            "file_url": "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
        }
    ]


def test_stream_knowledge_message_forwards_and_persists_statuses(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        playgrounds_service.playgrounds_repository,
        "get_session",
        lambda _database_url, *, owner_user_id, conversation_id, conversation_kind: {
            "id": conversation_id,
            "conversation_kind": "knowledge",
            "title": "Knowledge session",
            "title_source": "auto",
            "model_id": "safe-small",
            "knowledge_base_id": "kb-primary",
            "assistant_ref": "agent.knowledge_chat",
        } if conversation_kind == "knowledge" else None,
    )
    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "list_messages", lambda *_args, **_kwargs: [])

    def _fake_stream_knowledge_request(**_kwargs):
        yield {
            "event": "status",
            "data": {
                "id": "retrieval-1",
                "kind": "retrieving",
                "label": "Retrieved information from: kb_product_docs",
                "state": "completed",
                "duration_ms": 1200,
                "details": {"query": "hello knowledge"},
            },
        }
        yield {"event": "delta", "data": {"text": "knowledge "}}
        yield {"event": "delta", "data": {"text": "answer"}}
        yield {
            "event": "complete",
            "data": playgrounds_service.PlaygroundExecutionResult(
                output="knowledge answer",
                response={"id": "exec-1"},
                retrieval={"index": "kb_product_docs", "result_count": 1},
                knowledge_base_id="kb-primary",
            ),
        }

    monkeypatch.setattr(playgrounds_service, "stream_knowledge_request", _fake_stream_knowledge_request)

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
        lambda *_args, **_kwargs: {"id": "sess-knowledge", "playground_kind": "knowledge", "messages": []},
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

    events = list(playgrounds_service.stream_playground_message(
        "postgresql://ignored",
        config=config,
        request_id="req-knowledge-stream",
        owner_user_id=10,
        owner_role="user",
        session_id="sess-knowledge",
        prompt="hello knowledge",
    ))

    assert [event["event"] for event in events] == ["status", "delta", "delta", "complete"]
    assert events[0]["data"]["label"] == "Retrieved information from: kb_product_docs"
    assert [event["data"]["text"] for event in events if event["event"] == "delta"] == ["knowledge ", "answer"]
    assert captured["assistant_metadata"]["statuses"] == [events[0]["data"]]
    assert events[-1]["data"]["statuses"] == [events[0]["data"]]


def test_stream_chat_message_splits_first_token_wait_from_token_streaming(monkeypatch):
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

    def _fake_stream(**_kwargs):
        yield {
            "type": "transport",
            "phase": "upstream_response_headers",
            "duration_ms": 123,
            "status_code": 200,
            "endpoint_host": "api.openai.com",
            "duration_meaning": "provider queueing, prompt prefill, and first-stream setup",
            "headers": {"x-request-id": "req-chat-1"},
        }
        yield {"type": "delta", "text": "Hello"}
        yield {"type": "delta", "text": " world"}
        yield {
            "type": "complete",
            "response": {
                "output": [
                    {
                        "content": [{"type": "text", "text": "Hello world"}],
                    }
                ]
            },
        }

    def _append_message_pair(_database_url: str, **kwargs):
        captured.update(kwargs)
        return {
            "conversation": {"id": kwargs["conversation_id"]},
            "messages": [
                {"id": "msg-user", "role": "user", "content": kwargs["user_content"], "metadata_json": {}, "created_at": "2026-03-18T11:00:00+00:00"},
                {"id": "msg-assistant", "role": "assistant", "content": kwargs["assistant_content"], "metadata_json": kwargs["assistant_metadata"], "created_at": "2026-03-18T11:00:01+00:00"},
            ],
        }

    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "get_session", _get_session)
    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "list_messages", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playgrounds_service,
        "chat_completion_stream_with_allowed_model",
        lambda **_kwargs: (
            _fake_stream(),
            None,
            200,
            {
                "provider_slug": "openai-cloud",
                "provider_key": "openai_compatible_cloud_llm",
                "provider_origin": "cloud",
                "deployment_profile_slug": "online-cloud",
            },
        ),
    )
    monkeypatch.setattr(playgrounds_service.playgrounds_repository, "append_message_pair", _append_message_pair)
    monkeypatch.setattr(
        playgrounds_service,
        "get_playground_session_detail",
        lambda *_args, **_kwargs: {"id": "sess-chat", "playground_kind": "chat", "messages": []},
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

    events = list(playgrounds_service.stream_playground_message(
        "postgresql://ignored",
        config=config,
        request_id="req-chat-stream",
        owner_user_id=10,
        owner_role="user",
        session_id="sess-chat",
        prompt="hello",
    ))

    labels = [event["data"]["label"] for event in events if event["event"] == "status"]
    assert "Opening upstream stream" in labels
    assert "Provider queueing and stream setup complete" in labels
    assert "Waiting for first token" in labels
    assert "Received first token" in labels
    assert "Streaming response" in labels
    assert "Streamed response" in labels
    assert [event["data"]["text"] for event in events if event["event"] == "delta"] == ["Hello", " world"]
    assert events[-1]["event"] == "complete"
    assert captured["assistant_metadata"]["statuses"][-1]["label"] == "Streamed response"
    connected_status = next(
        status
        for status in captured["assistant_metadata"]["statuses"]
        if status["label"] == "Provider queueing and stream setup complete"
    )
    assert connected_status["summary"] == "request id req-chat-1"
    assert connected_status["details"]["endpoint_host"] == "api.openai.com"
    assert connected_status["details"]["provider_origin"] == "cloud"


def test_send_temporary_playground_message_does_not_persist(monkeypatch):
    monkeypatch.setattr(
        playgrounds_service,
        "chat_completion_with_allowed_model",
        lambda **_kwargs: (
            {
                "output": [
                    {
                        "content": [{"type": "text", "text": "temporary answer"}],
                    }
                ]
            },
            200,
        ),
    )
    monkeypatch.setattr(
        playgrounds_service.playgrounds_repository,
        "append_message_pair",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("temporary chat must not persist messages")),
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

    payload = playgrounds_service.send_temporary_playground_message(
        "postgresql://ignored",
        config=config,
        request_id="req-temporary",
        owner_user_id=10,
        owner_role="user",
        payload={
            "session_id": "temporary-chat-1",
            "playground_kind": "chat",
            "model_selection": {"model_id": "safe-small"},
            "knowledge_binding": {"knowledge_base_id": None},
            "messages": [{"role": "assistant", "content": "earlier", "metadata": {"statuses": [{"id": "old-status"}]}}],
            "prompt": "hello temporary",
        },
    )

    assert payload["output"] == "temporary answer"
    assert payload["session"]["id"] == "temporary-chat-1"
    assert payload["session"]["message_count"] == 3
    assert payload["session"]["messages"][0]["content"] == "earlier"
    assert payload["session"]["messages"][0]["metadata"]["statuses"] == [{"id": "old-status"}]
    assert payload["messages"][1]["content"] == "temporary answer"


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
