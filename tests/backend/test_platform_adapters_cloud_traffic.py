from __future__ import annotations

from app.services.cloud_traffic import subscribe_cloud_traffic_events
from app.services.platform_adapters import OpenAICompatibleEmbeddingsAdapter
from app.services.platform_types import ProviderBinding


def _binding(provider_origin: str) -> ProviderBinding:
    return ProviderBinding(
        capability_key="embeddings",
        provider_instance_id="provider-1",
        provider_slug="cloud-embeddings",
        provider_key="openai_compatible_cloud_embeddings",
        provider_origin=provider_origin,
        provider_display_name="Cloud embeddings",
        provider_description="",
        endpoint_url="https://api.example.com/v1",
        healthcheck_url=None,
        enabled=True,
        adapter_kind="openai_compatible_embeddings",
        config={"secret_refs": {"api_key": "test-key"}},
        binding_config={},
        deployment_profile_id="profile-1",
        deployment_profile_slug="online",
        deployment_profile_display_name="Online",
    )


def test_cloud_openai_compatible_request_emits_egress_and_ingress(monkeypatch):
    from app.services import platform_adapters

    def _request(*_args, **_kwargs):
        return {"data": [{"embedding": [1.0, 2.0]}]}, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = OpenAICompatibleEmbeddingsAdapter(_binding("cloud"))

    with subscribe_cloud_traffic_events() as queue:
        payload, status_code = adapter.embed_texts(texts=["hello"], model="text-embedding-test")

        egress = queue.get(timeout=1)
        ingress = queue.get(timeout=1)

    assert status_code == 200
    assert payload["embeddings"] == [[1.0, 2.0]]
    assert egress["direction"] == "egress"
    assert egress["operation"] == "embeddings.create"
    assert ingress["direction"] == "ingress"
    assert ingress["status_code"] == 200


def test_local_openai_compatible_request_emits_no_cloud_event(monkeypatch):
    from app.services import platform_adapters

    def _request(*_args, **_kwargs):
        return {"data": [{"embedding": [1.0, 2.0]}]}, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = OpenAICompatibleEmbeddingsAdapter(_binding("local"))

    with subscribe_cloud_traffic_events() as queue:
        adapter.embed_texts(texts=["hello"], model="text-embedding-test")

        assert queue.empty()
