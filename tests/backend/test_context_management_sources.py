from __future__ import annotations

import pytest

from app.services import context_management_shared
from app.services import context_management_sources
from app.services.platform_types import PlatformControlPlaneError


def test_normalize_knowledge_source_sync_failure_preserves_platform_error_message_and_code():
    exc = PlatformControlPlaneError(
        "knowledge_base_chunking_exceeds_embeddings_limit",
        "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens.",
        status_code=409,
        details={"safe_chunk_length_max": 254},
    )

    normalized = context_management_shared.normalize_knowledge_source_sync_failure(
        exc,
        source_id="source-1",
        source_display_name="Patient Guides",
        knowledge_base_id="kb-primary",
        sync_run_id="run-1",
    )

    assert normalized.message == "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens."
    assert normalized.error.code == "knowledge_base_chunking_exceeds_embeddings_limit"
    assert normalized.error.status_code == 409
    assert normalized.error.details == {
        "safe_chunk_length_max": 254,
        "source_id": "source-1",
        "source_display_name": "Patient Guides",
        "knowledge_base_id": "kb-primary",
        "sync_run_id": "run-1",
    }


def test_normalize_knowledge_source_sync_failure_wraps_unexpected_exception_with_fallback():
    normalized = context_management_shared.normalize_knowledge_source_sync_failure(
        RuntimeError(""),
        source_id="source-1",
        source_display_name="Patient Guides",
        knowledge_base_id="kb-primary",
        sync_run_id="run-1",
    )

    assert normalized.message == "Knowledge source sync failed."
    assert normalized.error.code == "knowledge_source_sync_failed"
    assert normalized.error.status_code == 500
    assert normalized.error.details == {
        "source_id": "source-1",
        "source_display_name": "Patient Guides",
        "knowledge_base_id": "kb-primary",
        "sync_run_id": "run-1",
        "original_exception_type": "RuntimeError",
        "original_exception_message": None,
    }


def test_sync_knowledge_source_persists_and_raises_the_same_chunking_failure(monkeypatch: pytest.MonkeyPatch):
    persisted: dict[str, object] = {}

    knowledge_base = {
      "id": "kb-primary",
      "index_name": "kb_product_docs",
      "schema_json": {},
    }
    source = {
      "id": "source-1",
      "display_name": "Patient Guides",
      "relative_path": "patient_guides",
      "include_globs": ["**/*.md"],
      "exclude_globs": [],
      "lifecycle_state": "active",
    }
    run = {
      "id": "run-1",
    }

    monkeypatch.setattr(context_management_sources, "_require_knowledge_base", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management_sources, "_require_knowledge_source", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(context_management_sources, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_sources, "_resolve_source_directory", lambda *_args, **_kwargs: ("patient_guides", object()))
    monkeypatch.setattr(context_management_sources, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_sources.context_repo, "mark_knowledge_source_syncing", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(context_management_sources.context_repo, "create_sync_run", lambda *_args, **_kwargs: run)
    monkeypatch.setattr(
        context_management_sources,
        "_sync_knowledge_source_documents",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PlatformControlPlaneError(
                "knowledge_base_chunking_exceeds_embeddings_limit",
                "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens.",
                status_code=409,
                details={"safe_chunk_length_max": 254},
            )
        ),
    )
    def _finish_sync_run(*_args, **kwargs):
        persisted["finished_run"] = kwargs
        return {"id": "run-1", "status": "error"}

    def _set_knowledge_source_sync_result(*_args, **kwargs):
        persisted["source_result"] = kwargs
        return {"id": "source-1", "last_sync_status": "error"}

    monkeypatch.setattr(context_management_sources.context_repo, "finish_sync_run", _finish_sync_run)
    monkeypatch.setattr(
        context_management_sources.context_repo,
        "set_knowledge_source_sync_result",
        _set_knowledge_source_sync_result,
    )
    monkeypatch.setattr(context_management_sources, "_mark_knowledge_base_sync_error", lambda *_args, **kwargs: persisted.setdefault("kb_error", kwargs))

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_sources.sync_knowledge_source(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            source_id="source-1",
            updated_by_user_id=1,
        )

    assert exc_info.value.code == "knowledge_base_chunking_exceeds_embeddings_limit"
    assert str(exc_info.value) == "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens."
    assert persisted["finished_run"]["error_summary"] == "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens."
    assert persisted["source_result"]["last_sync_error"] == "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens."


def test_sync_knowledge_source_wraps_unexpected_exception_with_persisted_message(monkeypatch: pytest.MonkeyPatch):
    persisted: dict[str, object] = {}

    knowledge_base = {
      "id": "kb-primary",
      "index_name": "kb_product_docs",
      "schema_json": {},
    }
    source = {
      "id": "source-1",
      "display_name": "Patient Guides",
      "relative_path": "patient_guides",
      "include_globs": ["**/*.md"],
      "exclude_globs": [],
      "lifecycle_state": "active",
    }
    run = {
      "id": "run-1",
    }

    monkeypatch.setattr(context_management_sources, "_require_knowledge_base", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management_sources, "_require_knowledge_source", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(context_management_sources, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_sources, "_resolve_source_directory", lambda *_args, **_kwargs: ("patient_guides", object()))
    monkeypatch.setattr(context_management_sources, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_sources.context_repo, "mark_knowledge_source_syncing", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(context_management_sources.context_repo, "create_sync_run", lambda *_args, **_kwargs: run)
    monkeypatch.setattr(
        context_management_sources,
        "_sync_knowledge_source_documents",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("")),
    )
    def _finish_sync_run(*_args, **kwargs):
        persisted["finished_run"] = kwargs
        return {"id": "run-1", "status": "error"}

    def _set_knowledge_source_sync_result(*_args, **kwargs):
        persisted["source_result"] = kwargs
        return {"id": "source-1", "last_sync_status": "error"}

    monkeypatch.setattr(context_management_sources.context_repo, "finish_sync_run", _finish_sync_run)
    monkeypatch.setattr(
        context_management_sources.context_repo,
        "set_knowledge_source_sync_result",
        _set_knowledge_source_sync_result,
    )
    monkeypatch.setattr(context_management_sources, "_mark_knowledge_base_sync_error", lambda *_args, **kwargs: persisted.setdefault("kb_error", kwargs))

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_sources.sync_knowledge_source(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            source_id="source-1",
            updated_by_user_id=1,
        )

    assert exc_info.value.code == "knowledge_source_sync_failed"
    assert str(exc_info.value) == "Knowledge source sync failed."
    assert exc_info.value.details["source_id"] == "source-1"
    assert exc_info.value.details["source_display_name"] == "Patient Guides"
    assert exc_info.value.details["knowledge_base_id"] == "kb-primary"
    assert exc_info.value.details["sync_run_id"] == "run-1"
    assert exc_info.value.details["last_sync_status"] == "error"
    assert exc_info.value.details["original_exception_type"] == "RuntimeError"
    assert exc_info.value.details["original_exception_message"] is None
    assert persisted["finished_run"]["error_summary"] == "Knowledge source sync failed."
    assert persisted["source_result"]["last_sync_error"] == "Knowledge source sync failed."
