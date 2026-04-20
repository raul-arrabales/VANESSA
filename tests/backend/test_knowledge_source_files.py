from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AuthConfig
from app.repositories import context_management as context_repo
from app.services import knowledge_source_files
from app.services.platform_types import PlatformControlPlaneError


def _config(source_root: Path) -> AuthConfig:
    return AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret",
        model_credentials_encryption_key="test-secret",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
        context_source_roots=(str(source_root),),
    )


def _runtime() -> dict[str, object]:
    return {
        "deployment_profile": {"slug": "local-default"},
        "capabilities": {
            "vector_store": {
                "resources": [
                    {
                        "id": "kb-primary",
                        "ref_type": "knowledge_base",
                        "knowledge_base_id": "kb-primary",
                        "provider_resource_id": "kb_product_docs",
                        "display_name": "Product Docs",
                    }
                ],
                "default_resource_id": "kb-primary",
                "resource_policy": {"selection_mode": "explicit"},
            }
        },
    }


def _patch_bound_kb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(knowledge_source_files, "get_active_platform_runtime", lambda *_args, **_kwargs: _runtime())
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_bases",
        lambda _db, _ids: [{"id": "kb-primary", "lifecycle_state": "active", "sync_status": "ready"}],
    )


def test_resolve_knowledge_source_file_serves_source_managed_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source_directory = tmp_path / "product_docs"
    source_directory.mkdir()
    source_file = source_directory / "guides" / "faq.md"
    source_file.parent.mkdir()
    source_file.write_text("# FAQ\n", encoding="utf-8")
    _patch_bound_kb(monkeypatch)
    monkeypatch.setattr(
        context_repo,
        "get_document",
        lambda *_args, **_kwargs: {
            "id": "doc-1",
            "knowledge_base_id": "kb-primary",
            "source_id": "source-1",
            "source_path": "guides/faq.md",
            "managed_by_source": True,
        },
    )
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_source",
        lambda *_args, **_kwargs: {
            "id": "source-1",
            "knowledge_base_id": "kb-primary",
            "source_type": "local_directory",
            "relative_path": "product_docs",
        },
    )

    resolved = knowledge_source_files.resolve_knowledge_source_file(
        "ignored",
        config=_config(tmp_path),
        knowledge_base_id="kb-primary",
        document_id="doc-1",
    )

    assert resolved.path == source_file.resolve()
    assert resolved.as_attachment is False
    assert resolved.download_name == "faq.md"


def test_resolve_knowledge_source_file_rejects_manual_documents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _patch_bound_kb(monkeypatch)
    monkeypatch.setattr(
        context_repo,
        "get_document",
        lambda *_args, **_kwargs: {
            "id": "doc-1",
            "knowledge_base_id": "kb-primary",
            "source_id": None,
            "source_path": None,
            "managed_by_source": False,
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        knowledge_source_files.resolve_knowledge_source_file(
            "ignored",
            config=_config(tmp_path),
            knowledge_base_id="kb-primary",
            document_id="doc-1",
        )

    assert exc_info.value.code == "source_file_not_available"
    assert exc_info.value.status_code == 409


def test_resolve_knowledge_source_file_resists_path_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source_directory = tmp_path / "product_docs"
    source_directory.mkdir()
    _patch_bound_kb(monkeypatch)
    monkeypatch.setattr(
        context_repo,
        "get_document",
        lambda *_args, **_kwargs: {
            "id": "doc-1",
            "knowledge_base_id": "kb-primary",
            "source_id": "source-1",
            "source_path": "../secret.txt",
            "managed_by_source": True,
        },
    )
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_source",
        lambda *_args, **_kwargs: {
            "id": "source-1",
            "knowledge_base_id": "kb-primary",
            "source_type": "local_directory",
            "relative_path": "product_docs",
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        knowledge_source_files.resolve_knowledge_source_file(
            "ignored",
            config=_config(tmp_path),
            knowledge_base_id="kb-primary",
            document_id="doc-1",
        )

    assert exc_info.value.code == "invalid_source_file_path"
    assert exc_info.value.status_code == 404


def test_resolve_knowledge_source_file_requires_bound_ready_kb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(knowledge_source_files, "get_active_platform_runtime", lambda *_args, **_kwargs: _runtime())
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_bases",
        lambda _db, _ids: [{"id": "kb-primary", "lifecycle_state": "active", "sync_status": "error"}],
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        knowledge_source_files.resolve_knowledge_source_file(
            "ignored",
            config=_config(tmp_path),
            knowledge_base_id="kb-primary",
            document_id="doc-1",
        )

    assert exc_info.value.code == "knowledge_base_not_configured"
    assert exc_info.value.status_code == 409
