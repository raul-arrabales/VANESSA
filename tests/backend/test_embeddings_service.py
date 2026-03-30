from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import embeddings_service  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402


def _fake_binding() -> SimpleNamespace:
    return SimpleNamespace(
        provider_instance_id="provider-embeddings",
        provider_slug="vllm-embeddings-local",
        provider_key="vllm_embeddings_local",
        provider_display_name="vLLM embeddings local",
        deployment_profile_slug="local-default",
        default_resource_id="sentence-transformers--all-MiniLM-L6-v2",
        default_resource={},
    )


class _FakeEmbeddingsAdapter:
    def __init__(self, responses: list[tuple[dict[str, object] | None, int]]) -> None:
        self.binding = _fake_binding()
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def embed_texts(self, *, texts: list[str], model: str | None = None):
        self.calls.append({"texts": list(texts), "model": model})
        return self._responses.pop(0)


def test_embed_text_inputs_with_target_recovers_local_embeddings_runtime_once(monkeypatch: pytest.MonkeyPatch):
    adapter = _FakeEmbeddingsAdapter(
        [
            ({"detail": {"code": "model_not_found"}}, 404),
            ({"embeddings": [[0.1, 0.2]], "embedding_dimension": 2}, 200),
        ]
    )
    recovery_calls: list[dict[str, object]] = []
    provider_row = {
        "id": "provider-embeddings",
        "provider_key": "vllm_embeddings_local",
        "capability_key": "embeddings",
        "adapter_kind": "openai_compatible_embeddings",
    }
    monkeypatch.setattr(embeddings_service, "resolve_embeddings_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(
        embeddings_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: provider_row if provider_instance_id == "provider-embeddings" else None,
    )
    monkeypatch.setattr(
        embeddings_service,
        "recover_provider_local_slot_runtime",
        lambda _db, *, provider_row, force=False: (
            recovery_calls.append({"provider_row": dict(provider_row), "force": force})
            or (provider_row, True, {
                "has_persisted_intent": True,
                "runtime_empty": True,
                "target_available": False,
                "slot": {"loaded_managed_model_id": "sentence-transformers--all-MiniLM-L6-v2"},
                "runtime_model_id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
                "runtime_inventory_ids": [],
                "runtime_state": {"load_state": "loading"},
            })
        ),
    )

    payload = embeddings_service.embed_text_inputs_with_target(
        "ignored",
        object(),  # type: ignore[arg-type]
        ["hello world"],
        provider_instance_id="provider-embeddings",
        model="/models/llm/sentence-transformers--all-MiniLM-L6-v2",
    )

    assert payload["count"] == 1
    assert payload["dimension"] == 2
    assert payload["embeddings"] == [[0.1, 0.2]]
    assert recovery_calls == [{"provider_row": provider_row, "force": True}]
    assert len(adapter.calls) == 2


def test_embed_text_inputs_with_target_surfaces_actionable_local_runtime_drift_error(
    monkeypatch: pytest.MonkeyPatch,
):
    adapter = _FakeEmbeddingsAdapter(
        [
            ({"detail": {"code": "model_not_found"}}, 404),
            ({"detail": {"code": "model_not_found"}}, 404),
        ]
    )
    provider_row = {
        "id": "provider-embeddings",
        "provider_key": "vllm_embeddings_local",
        "capability_key": "embeddings",
        "adapter_kind": "openai_compatible_embeddings",
    }
    monkeypatch.setattr(embeddings_service, "resolve_embeddings_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(
        embeddings_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: provider_row if provider_instance_id == "provider-embeddings" else None,
    )
    monkeypatch.setattr(
        embeddings_service,
        "recover_provider_local_slot_runtime",
        lambda _db, *, provider_row, force=False: (
            provider_row,
            True,
            {
                "has_persisted_intent": True,
                "runtime_empty": True,
                "target_available": False,
                "slot": {"loaded_managed_model_id": "sentence-transformers--all-MiniLM-L6-v2"},
                "runtime_model_id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
                "runtime_inventory_ids": [],
                "runtime_state": {"load_state": "empty"},
            },
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        embeddings_service.embed_text_inputs_with_target(
            "ignored",
            object(),  # type: ignore[arg-type]
            ["hello world"],
            provider_instance_id="provider-embeddings",
            model="/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        )

    assert exc_info.value.code == "embeddings_runtime_drift"
    assert "local embeddings runtime is empty or out of sync" in exc_info.value.message
    assert exc_info.value.status_code == 503

