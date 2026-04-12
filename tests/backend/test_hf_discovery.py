from __future__ import annotations

import sys
import types
from datetime import datetime, timezone

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


def test_discover_hf_models_offsets_results(monkeypatch):
    captured: dict[str, object] = {}

    class FakeModel:
        def __init__(self, model_id: str):
            self.id = model_id
            self.downloads = 10
            self.likes = 1
            self.tags = ["text-generation"]

    class FakeHfApi:
        def __init__(self, token=None):
            self.token = token

        def list_models(self, **kwargs):
            captured["kwargs"] = kwargs
            return [FakeModel(f"org/model-{index}") for index in range(5)]

    fake_module = types.SimpleNamespace(HfApi=FakeHfApi)

    monkeypatch.setattr(hf_discovery, "assert_internet_allowed", lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)

    results = hf_discovery.discover_hf_models(
        database_url="postgresql://example",
        query="llama",
        task="text-generation",
        sort="downloads",
        limit=2,
        offset=2,
        token=None,
    )

    assert captured["kwargs"]["limit"] == 4
    assert [result["source_id"] for result in results] == ["org/model-2", "org/model-3"]


def test_get_hf_model_details_maps_rich_metadata(monkeypatch):
    class FakeCardData:
        def to_dict(self):
            return {"license": "apache-2.0", "language": ["en"]}

    class FakeLfs:
        def __init__(self):
            self.oid = "sha256:abc"
            self.size = 12345

    class FakeSibling:
        def __init__(self, rfilename: str, size: int, blob_id: str | None = None, lfs=None):
            self.rfilename = rfilename
            self.size = size
            self.blob_id = blob_id
            self.lfs = lfs

    class FakeInfo:
        id = "meta-llama/Llama-3-8B-Instruct"
        sha = "abc123"
        downloads = 1234
        likes = 99
        tags = ["text-generation", "safetensors"]
        author = "meta-llama"
        pipeline_tag = "text-generation"
        library_name = "transformers"
        gated = "manual"
        private = False
        disabled = False
        created_at = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
        lastModified = datetime(2026, 1, 3, 3, 4, tzinfo=timezone.utc)
        usedStorage = 2048
        cardData = FakeCardData()
        config = {"architectures": ["LlamaForCausalLM"], "model_type": "llama"}
        safetensors = {"total": 1}
        model_index = [{"name": "llama"}]
        transformersInfo = {"auto_model": "AutoModelForCausalLM"}
        siblings = [
            FakeSibling("model-00001-of-00002.safetensors", 1024, "blob-1", FakeLfs()),
            FakeSibling("config.json", 256),
        ]

    class FakeHfApi:
        def __init__(self, token=None):
            self.token = token

        def model_info(self, repo_id: str, files_metadata: bool):
            assert repo_id == "meta-llama/Llama-3-8B-Instruct"
            assert files_metadata is True
            return FakeInfo()

    fake_module = types.SimpleNamespace(HfApi=FakeHfApi)

    monkeypatch.setattr(hf_discovery, "assert_internet_allowed", lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)

    result = hf_discovery.get_hf_model_details(
        "meta-llama/Llama-3-8B-Instruct",
        database_url="postgresql://example",
        token="hf-token",
    )

    assert result["source_id"] == "meta-llama/Llama-3-8B-Instruct"
    assert result["pipeline_tag"] == "text-generation"
    assert result["library_name"] == "transformers"
    assert result["created_at"] == "2026-01-02T03:04:00+00:00"
    assert result["last_modified"] == "2026-01-03T03:04:00+00:00"
    assert result["used_storage"] == 2048
    assert result["card_data"] == {"license": "apache-2.0", "language": ["en"]}
    assert result["config"]["model_type"] == "llama"
    assert result["safetensors"] == {"total": 1}
    assert result["model_index"] == [{"name": "llama"}]
    assert result["transformers_info"] == {"auto_model": "AutoModelForCausalLM"}
    assert result["files"][0] == {
        "path": "model-00001-of-00002.safetensors",
        "size": 1024,
        "file_type": "safetensors",
        "blob_id": "blob-1",
        "lfs": {"oid": "sha256:abc", "size": 12345},
    }
    assert result["files"][1] == {
        "path": "config.json",
        "size": 256,
        "file_type": "json",
    }
