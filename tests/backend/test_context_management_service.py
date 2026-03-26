from __future__ import annotations

import io

import pytest
from werkzeug.datastructures import FileStorage

from app.services import context_management  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402


def test_parse_upload_documents_supports_text_and_jsonl():
    text_file = FileStorage(stream=io.BytesIO(b"Hello knowledge base"), filename="notes.txt")
    jsonl_file = FileStorage(
        stream=io.BytesIO(b'{"title":"Doc A","text":"Alpha"}\n{"title":"Doc B","content":"Beta"}\n'),
        filename="docs.jsonl",
    )

    parsed_text = context_management._parse_upload_documents(text_file)  # type: ignore[attr-defined]
    parsed_jsonl = context_management._parse_upload_documents(jsonl_file)  # type: ignore[attr-defined]

    assert parsed_text == [
        {
            "title": "notes",
            "source_type": "upload",
            "source_name": "notes.txt",
            "text": "Hello knowledge base",
            "metadata": {},
        }
    ]
    assert [item["title"] for item in parsed_jsonl] == ["Doc A", "Doc B"]
    assert [item["text"] for item in parsed_jsonl] == ["Alpha", "Beta"]


def test_delete_knowledge_base_rejects_bound_deployments(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management.context_repo,
        "get_knowledge_base",
        lambda _db, _knowledge_base_id: {"id": "kb-primary", "index_name": "kb_product_docs", "backing_provider_key": "weaviate_local"},
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "count_deployment_bindings_for_knowledge_base",
        lambda _db, *, knowledge_base_id: 2,
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management.delete_knowledge_base(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            knowledge_base_id="kb-primary",
        )

    assert exc_info.value.code == "knowledge_base_in_use"
