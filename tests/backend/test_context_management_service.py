from __future__ import annotations

import pytest

from app.application import context_management_service


def test_create_context_knowledge_base_requires_json_object() -> None:
    with pytest.raises(context_management_service.ContextManagementRequestError) as exc_info:
        context_management_service.create_context_knowledge_base(
            "postgresql://ignored",
            config=object(),
            payload=[],
            created_by_user_id=10,
        )

    assert exc_info.value.code == "invalid_payload"


def test_create_context_knowledge_source_requires_json_object() -> None:
    with pytest.raises(context_management_service.ContextManagementRequestError) as exc_info:
        context_management_service.create_context_knowledge_source(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-1",
            payload=[],
            created_by_user_id=10,
        )

    assert exc_info.value.code == "invalid_payload"


def test_upload_context_knowledge_base_documents_passes_files_through(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _upload_documents(_database_url: str, *, config, knowledge_base_id: str, files, metadata, created_by_user_id: int):
        captured["config"] = config
        captured["knowledge_base_id"] = knowledge_base_id
        captured["files"] = files
        captured["metadata"] = metadata
        captured["created_by_user_id"] = created_by_user_id
        return {"uploaded": len(files)}

    monkeypatch.setattr(context_management_service, "_upload_knowledge_base_documents", _upload_documents)

    payload = context_management_service.upload_context_knowledge_base_documents(
        "postgresql://ignored",
        config="config",
        knowledge_base_id="kb-1",
        files=["file-a", "file-b"],
        metadata={"topic": "ops"},
        created_by_user_id=22,
    )

    assert captured == {
        "config": "config",
        "knowledge_base_id": "kb-1",
        "files": ["file-a", "file-b"],
        "metadata": {"topic": "ops"},
        "created_by_user_id": 22,
    }
    assert payload == {"uploaded": 2}
