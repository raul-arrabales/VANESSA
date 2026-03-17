from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services import runtime_client  # noqa: E402


def _platform_runtime(*, provider_key: str = "vllm_local", request_format: str = "responses_api") -> dict[str, object]:
    return {
        "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
        "capabilities": {
            "llm_inference": {
                "id": "provider-1",
                "slug": "llm-provider",
                "provider_key": provider_key,
                "display_name": "LLM Provider",
                "description": "desc",
                "adapter_kind": "openai_compatible_llm",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config": {
                    "chat_completion_path": "/v1/chat/completions",
                    "request_format": request_format,
                    "forced_model_id": "local-default-model",
                },
                "binding_config": {},
            }
        },
    }


def test_openai_compatible_runtime_client_supports_vanessa_gateway_payloads(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"output": [{"role": "assistant", "content": [{"type": "text", "text": "gateway reply"}]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(_platform_runtime())

    payload = client.chat_completion(
        requested_model="model.alpha",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert payload == {
        "output_text": "gateway reply",
        "status_code": 200,
        "requested_model": "model.alpha",
    }
    assert seen_payloads == [
        {
            "model": "model.alpha",
            "input": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        }
    ]


def test_openai_compatible_runtime_client_supports_openai_chat_responses(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"choices": [{"message": {"role": "assistant", "content": "llama.cpp reply"}}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(
        _platform_runtime(provider_key="llama_cpp_local", request_format="openai_chat")
    )

    payload = client.chat_completion(
        requested_model=None,
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert payload == {
        "output_text": "llama.cpp reply",
        "status_code": 200,
        "requested_model": "local-default-model",
    }
    assert seen_payloads == [
        {
            "model": "local-default-model",
            "messages": [{"role": "user", "content": "hello"}],
        }
    ]


def test_openai_compatible_runtime_client_maps_transport_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_client, "http_json_request", lambda *args, **kwargs: (None, 504))
    client = runtime_client.build_llm_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.LlmRuntimeClientError) as exc_info:
        client.chat_completion(
            requested_model="model.alpha",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )

    assert exc_info.value.code == "runtime_unreachable"
