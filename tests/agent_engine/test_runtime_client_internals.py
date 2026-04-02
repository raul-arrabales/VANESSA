from __future__ import annotations

import io
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services.runtime_clients import resolution, transport, vector_store  # noqa: E402
from agent_engine.app.services.runtime_clients.base import EmbeddingsRuntimeClientError  # noqa: E402


class _FakeResponse:
    def __init__(self, *, status: int, body: str):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


def test_http_json_request_returns_body_for_invalid_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transport, "urlopen", lambda *_args, **_kwargs: _FakeResponse(status=200, body="not-json"))

    payload, status_code = transport.http_json_request("http://example.com/test", method="GET")

    assert status_code == 200
    assert payload == {"body": "not-json"}


def test_http_json_request_preserves_non_json_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_http_error(*_args, **_kwargs):
        raise HTTPError(
            url="http://example.com/test",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b"temporarily unavailable"),
        )

    monkeypatch.setattr(transport, "urlopen", _raise_http_error)

    payload, status_code = transport.http_json_request("http://example.com/test", method="GET")

    assert status_code == 503
    assert payload == {"error": "upstream_error", "body": "temporarily unavailable"}


def test_binding_timeout_seconds_parses_positive_values_and_falls_back() -> None:
    assert resolution.binding_timeout_seconds({"config": {"request_timeout_seconds": "7.5"}}) == 7.5
    assert resolution.binding_timeout_seconds({"config": {"request_timeout_seconds": 0}}) == transport.DEFAULT_HTTP_TIMEOUT_SECONDS
    assert resolution.binding_timeout_seconds({"config": {"request_timeout_seconds": "oops"}}) == transport.DEFAULT_HTTP_TIMEOUT_SECONDS


def test_resolve_runtime_model_identifier_uses_loaded_runtime_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_timeouts: list[float] = []
    binding = {
        "slug": "vllm-embeddings-local",
        "endpoint_url": "http://llm:8000",
        "config": {
            "models_path": "/v1/models",
            "request_timeout_seconds": 42,
            "loaded_runtime_model_id": "loaded",
            "loaded_local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        },
    }
    resource = {
        "id": "sentence-transformers--all-MiniLM-L6-v2",
        "provider_resource_id": None,
        "managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
        "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        "metadata": {
            "provider_model_id": None,
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        },
    }

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, payload, headers
        seen_timeouts.append(timeout_seconds)
        return {"data": [{"id": "loaded"}]}, 200

    resolved = resolution.resolve_runtime_model_identifier(
        binding=binding,
        resource=resource,
        error_cls=EmbeddingsRuntimeClientError,
        request_json=_request,
    )

    assert resolved == "loaded"
    assert seen_timeouts == [42.0]


def test_build_weaviate_query_operation_balances_braces() -> None:
    operation = vector_store.build_weaviate_query_operation(
        class_name="KnowledgeBase",
        embedding=[0.1, 0.2],
        top_k=4,
        filters={"tenant": "ops"},
    )

    assert operation["query"].count("{") == operation["query"].count("}")
    assert 'where: { path: ["tenant"], operator: Equal, valueText: "ops" }' in operation["query"]
