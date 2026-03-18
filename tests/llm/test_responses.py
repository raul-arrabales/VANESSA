from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_PATH = PROJECT_ROOT / "llm"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]
if str(LLM_PATH) in sys.path:
    sys.path.remove(str(LLM_PATH))
sys.path.insert(0, str(LLM_PATH))
llm_app_package = types.ModuleType("app")
llm_app_package.__path__ = [str(LLM_PATH / "app")]
sys.modules["app"] = llm_app_package

from app.main import _iter_streaming_response_chunks, create_chat_completion, create_embeddings, create_response  # noqa: E402
from app.providers.openai_compat import OpenAICompatibleProvider  # noqa: E402
from app.providers.base import ProviderError  # noqa: E402
from app.registry import registry  # noqa: E402
from app.schemas import EmbeddingRequest, ResponseRequest  # noqa: E402


def test_unknown_model_returns_not_found() -> None:
    request = ResponseRequest(
        model="missing-model",
        input=[{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
    )

    with pytest.raises(HTTPException) as exc:
        create_response(request)

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "model_not_found"


def test_dummy_model_returns_deterministic_response() -> None:
    request = ResponseRequest(
        model="dummy",
        temperature=0,
        max_tokens=12,
        input=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
    )

    response = create_chat_completion(request)

    assert response.model == "dummy"
    assert response.error is None
    assert response.output[0].content[0].text == "Hello, this is the test dummy model."
    assert response.usage.total_tokens == (
        response.usage.prompt_tokens + response.usage.completion_tokens
    )


def test_multimodal_payload_validation_rejects_unsupported_image_input() -> None:
    request = ResponseRequest(
        model="dummy",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "b64_json": "iVBORw0KGgoAAAANSUhEUgAA",
                        },
                    },
                ],
            }
        ],
    )

    with pytest.raises(HTTPException) as exc:
        create_response(request)

    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "unsupported_input"


def test_multimodal_payload_validation_rejects_invalid_image_part() -> None:
    with pytest.raises(ValidationError):
        ResponseRequest(
            model="dummy",
            input=[
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {}}],
                }
            ],
        )


def test_provider_error_maps_to_http_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    request = ResponseRequest(
        model="dummy",
        input=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
    )
    resolved = registry.resolve_model("dummy")

    def fail_generate(self, _request: ResponseRequest, *, upstream_model: str):
        _ = (self, _request, upstream_model)
        raise ProviderError(
            status_code=429,
            code="dummy_rate_limited",
            message="rate limited",
        )

    monkeypatch.setattr(type(resolved.provider), "generate", fail_generate)

    with pytest.raises(HTTPException) as exc:
        create_chat_completion(request)
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "dummy_rate_limited"


def test_local_embeddings_model_returns_embedding_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    request = EmbeddingRequest(model="local-vllm-embeddings-default", input=["hello"])
    resolved = registry.resolve_model("local-vllm-embeddings-default")

    def fake_embed(self, _request: EmbeddingRequest, *, upstream_model: str):
        _ = self
        assert upstream_model
        assert _request.input == ["hello"]
        return type("EmbeddingResult", (), {"embeddings": [[0.1, 0.2]], "prompt_tokens": 3})()

    monkeypatch.setattr(type(resolved.provider), "embed", fake_embed)

    response = create_embeddings(request)

    assert response.object == "list"
    assert response.model == "local-vllm-embeddings-default"
    assert response.data[0].embedding == [0.1, 0.2]
    assert response.usage.prompt_tokens == 3
    assert response.usage.total_tokens == 3


def test_embeddings_reject_models_without_embedding_capability() -> None:
    request = EmbeddingRequest(model="dummy", input=["hello"])

    with pytest.raises(HTTPException) as exc:
        create_embeddings(request)

    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "unsupported_input"


def test_chat_completion_normalizes_provider_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    request = ResponseRequest(
        model="dummy",
        input=[{"role": "user", "content": [{"type": "text", "text": "Search for hello"}]}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web",
                    "parameters": {"type": "object"},
                },
            }
        ],
    )
    resolved = registry.resolve_model("dummy")

    def fake_generate(self, _request: ResponseRequest, *, upstream_model: str):
        _ = (self, upstream_model)
        assert _request.tools[0].function.name == "web_search"
        return type(
            "ProviderResult",
            (),
            {
                "output_text": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "web_search", "arguments": "{\"query\":\"hello\"}"},
                    }
                ],
                "prompt_tokens": 2,
                "completion_tokens": 0,
            },
        )()

    monkeypatch.setattr(type(resolved.provider), "generate", fake_generate)

    response = create_chat_completion(request)

    assert response.output[0].tool_calls[0].function.name == "web_search"
    assert response.output[0].content == []


def test_streaming_response_chunks_emit_delta_then_complete() -> None:
    request = ResponseRequest(
        model="dummy",
        input=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
        stream=True,
    )

    chunks = list(_iter_streaming_response_chunks(request))

    assert chunks[0].startswith("event: delta\n")
    assert '"text": "Hello, this is the test dummy model."' in chunks[0]
    assert chunks[-1].startswith("event: complete\n")
    assert '"response"' in chunks[-1]


def test_streaming_response_chunks_emit_error_after_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    request = ResponseRequest(
        model="dummy",
        input=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
        stream=True,
    )
    resolved = registry.resolve_model("dummy")

    def fail_generate_stream(self, _request: ResponseRequest, *, upstream_model: str):
        _ = (self, _request, upstream_model)
        raise ProviderError(
            status_code=502,
            code="dummy_failed",
            message="stream failed",
        )

    monkeypatch.setattr(type(resolved.provider), "generate_stream", fail_generate_stream)

    chunks = list(_iter_streaming_response_chunks(request))

    assert chunks[-1].startswith("event: error\n")
    assert '"error": "dummy_failed"' in chunks[-1]


def test_openai_compatible_provider_parses_streamed_sse_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://example.test/v1",
        auth_header_value=None,
        provider_code_prefix="local_vllm",
        timeout_seconds=5,
    )
    request = ResponseRequest(
        model="dummy",
        input=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
        stream=True,
    )

    class FakeResponse:
        def __init__(self):
            self._lines = iter(
                [
                    b"data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n",
                    b"\n",
                    b"data: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}],\"usage\":{\"prompt_tokens\":3,\"completion_tokens\":2}}\n",
                    b"\n",
                    b"data: [DONE]\n",
                    b"\n",
                ]
            )

        def readline(self):
            return next(self._lines, b"")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

    monkeypatch.setattr("app.providers.openai_compat.urlopen", lambda *_args, **_kwargs: FakeResponse())

    events = list(provider.generate_stream(request, upstream_model="dummy"))

    assert events == [
        {"type": "delta", "text": "Hel"},
        {"type": "delta", "text": "lo"},
        {"type": "complete", "prompt_tokens": 3, "completion_tokens": 2},
    ]
