from __future__ import annotations

from pathlib import Path

from app.services.context_management_ingestion import _parse_source_documents


def test_parse_source_documents_merges_source_metadata(tmp_path: Path) -> None:
    source_file = tmp_path / "guide.txt"
    source_file.write_text("Hello world", encoding="utf-8")

    payload = _parse_source_documents(
        source_file,
        relative_path="guides/guide.txt",
        source={
            "display_name": "Docs folder",
            "metadata_json": {
                "category": "guide",
                "published": True,
            },
        },
    )

    assert payload[0]["metadata"]["category"] == "guide"
    assert payload[0]["metadata"]["published"] is True
    assert payload[0]["metadata"]["source_path"] == "guides/guide.txt"
    assert payload[0]["metadata"]["source_display_name"] == "Docs folder"
