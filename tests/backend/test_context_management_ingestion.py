from __future__ import annotations

from app.services.context_management_ingestion import _iter_source_files


NEW_DEFAULT_INCLUDE_GLOBS = [
    "*.md",
    "*.txt",
    "*.pdf",
    "*.json",
    "*.jsonl",
    "**/*.md",
    "**/*.txt",
    "**/*.pdf",
    "**/*.json",
    "**/*.jsonl",
]


def test_iter_source_files_matches_root_and_nested_pdfs_with_explicit_default_globs(tmp_path):
    root_pdf = tmp_path / "root.pdf"
    nested_dir = tmp_path / "nested"
    nested_pdf = nested_dir / "child.pdf"
    root_pdf.write_bytes(b"%PDF-1.4 root")
    nested_dir.mkdir()
    nested_pdf.write_bytes(b"%PDF-1.4 nested")

    matched = _iter_source_files(
        tmp_path,
        include_globs=NEW_DEFAULT_INCLUDE_GLOBS,
        exclude_globs=[],
    )

    assert [(path.name, relative_path) for path, relative_path in matched] == [
        ("child.pdf", "nested/child.pdf"),
        ("root.pdf", "root.pdf"),
    ]


def test_iter_source_files_does_not_match_pdfs_with_brace_style_glob(tmp_path):
    root_pdf = tmp_path / "root.pdf"
    nested_dir = tmp_path / "nested"
    nested_pdf = nested_dir / "child.pdf"
    root_pdf.write_bytes(b"%PDF-1.4 root")
    nested_dir.mkdir()
    nested_pdf.write_bytes(b"%PDF-1.4 nested")

    matched = _iter_source_files(
        tmp_path,
        include_globs=["**/*.{md,txt,pdf,json,jsonl}"],
        exclude_globs=[],
    )

    assert matched == []
