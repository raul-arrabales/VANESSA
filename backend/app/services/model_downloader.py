from __future__ import annotations

import os
import re
from pathlib import Path

_SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_source_id(source_id: str) -> str:
    normalized = source_id.strip().replace("\\", "/")
    normalized = normalized.strip("/")
    normalized = normalized.replace("/", "--")
    safe = _SAFE_NAME_PATTERN.sub("-", normalized).strip("-")
    if not safe:
        raise ValueError("invalid_source_id")
    return safe


def resolve_target_dir(storage_root: str, source_id: str) -> str:
    root = Path(storage_root).resolve()
    safe_dir_name = sanitize_source_id(source_id)
    target = (root / safe_dir_name).resolve()
    if root != target and root not in target.parents:
        raise ValueError("invalid_target_dir")
    return str(target)


def download_from_huggingface(
    *,
    source_id: str,
    storage_root: str,
    token: str | None,
    allow_patterns: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
) -> str:
    from huggingface_hub import snapshot_download

    target_dir = resolve_target_dir(storage_root, source_id)
    os.makedirs(target_dir, exist_ok=True)
    snapshot_download(
        repo_id=source_id,
        token=token or None,
        local_dir=target_dir,
        allow_patterns=allow_patterns or None,
        ignore_patterns=ignore_patterns or None,
        max_workers=4,
    )
    return target_dir
