from __future__ import annotations

import sys
import types

from app.services import hf_discovery


def test_discover_hf_models_calls_hf_api_without_direction(monkeypatch):
    captured: dict[str, object] = {}

    class FakeHfApi:
        def __init__(self, token=None):
            captured["token"] = token

        def list_models(self, **kwargs):
            captured["kwargs"] = kwargs
            return []

    fake_module = types.SimpleNamespace(HfApi=FakeHfApi)

    monkeypatch.setattr(hf_discovery, "assert_internet_allowed", lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)

    results = hf_discovery.discover_hf_models(
        database_url="postgresql://example",
        query="llama",
        task="text-generation",
        sort="downloads",
        limit=12,
        token="hf-token",
    )

    assert results == []
    assert captured["token"] == "hf-token"
    assert captured["kwargs"] == {
        "search": "llama",
        "filter": "text-generation",
        "sort": "downloads",
        "limit": 12,
    }


def test_discover_hf_models_maps_hf_results(monkeypatch):
    class FakeModel:
        def __init__(self, model_id: str, downloads: int, likes: int, tags: list[str]):
            self.id = model_id
            self.downloads = downloads
            self.likes = likes
            self.tags = tags

    class FakeHfApi:
        def __init__(self, token=None):
            self.token = token

        def list_models(self, **kwargs):
            return [
                FakeModel("meta-llama/Llama-3-8B-Instruct", 1234, 99, ["text-generation", "llm"]),
            ]

    fake_module = types.SimpleNamespace(HfApi=FakeHfApi)

    monkeypatch.setattr(hf_discovery, "assert_internet_allowed", lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)

    results = hf_discovery.discover_hf_models(
        database_url="postgresql://example",
        query="llama",
        task="text-generation",
        sort="downloads",
        limit=10,
        token=None,
    )

    assert results == [
        {
            "source_id": "meta-llama/Llama-3-8B-Instruct",
            "name": "Llama-3-8B-Instruct",
            "downloads": 1234,
            "likes": 99,
            "tags": ["text-generation", "llm"],
            "provider": "huggingface",
        },
    ]
