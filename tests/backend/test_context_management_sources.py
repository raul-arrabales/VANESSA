from __future__ import annotations

import pytest

from app.config import AuthConfig
from app.services.context_management_sources import list_source_directories
from app.services.platform_types import PlatformControlPlaneError
from tests.backend.support.auth_harness import build_test_auth_config


def _config_for_roots(*roots: str) -> AuthConfig:
    return build_test_auth_config(AuthConfig, context_source_roots=tuple(roots))


def test_list_source_directories_returns_roots_and_child_directories(tmp_path):
    docs = tmp_path / "product_docs"
    guides = docs / "guides"
    docs.mkdir()
    guides.mkdir()
    (tmp_path / "archive").mkdir()

    payload = list_source_directories(config=_config_for_roots(str(tmp_path)))

    assert payload["roots"][0]["display_name"] == str(tmp_path.resolve())
    assert payload["selected_root_id"]
    assert payload["current_relative_path"] == ""
    assert payload["parent_relative_path"] is None
    assert payload["directories"] == [
        {"name": "archive", "relative_path": "archive"},
        {"name": "product_docs", "relative_path": "product_docs"},
    ]


def test_list_source_directories_returns_nested_parent_path(tmp_path):
    docs = tmp_path / "product_docs"
    guides = docs / "guides"
    docs.mkdir()
    guides.mkdir()

    payload = list_source_directories(
        config=_config_for_roots(str(tmp_path)),
        relative_path="product_docs",
    )

    assert payload["current_relative_path"] == "product_docs"
    assert payload["parent_relative_path"] == ""
    assert payload["directories"] == [{"name": "guides", "relative_path": "product_docs/guides"}]


def test_list_source_directories_rejects_escape_paths(tmp_path):
    with pytest.raises(PlatformControlPlaneError) as exc_info:
        list_source_directories(
            config=_config_for_roots(str(tmp_path)),
            relative_path="../outside",
        )

    assert exc_info.value.code == "invalid_source_relative_path"
