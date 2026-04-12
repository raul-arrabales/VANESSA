from __future__ import annotations

import types

import pytest

from app.application import modelops_local_service
from app.services.modelops_common import ModelOpsError


def test_normalize_discovery_request_maps_embedding_task_key() -> None:
    request = modelops_local_service.normalize_discovery_request(
        query="embed",
        task_key="embeddings",
        task=None,
        sort="downloads",
        limit="5",
        offset="10",
    )
    assert request["task"] == "feature-extraction"
    assert request["limit"] == 5
    assert request["offset"] == 10


def test_normalize_download_request_requires_source_id() -> None:
    config = types.SimpleNamespace(
        model_storage_root="/models/llm",
        model_download_allow_patterns_default="",
        model_download_ignore_patterns_default="",
    )

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_local_service.normalize_download_request({}, config=config, current_user_id=1)

    assert exc_info.value.code == "invalid_source_id"
