from __future__ import annotations

from datetime import date, datetime
from itertools import islice
from typing import Any

from .connectivity_policy import assert_internet_allowed


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        try:
            return _json_safe(value.to_dict())
        except TypeError:
            pass
    if hasattr(value, "__dict__"):
        return {
            key: _json_safe(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return str(value)


def _first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _add_optional(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = _json_safe(value)


def _file_type(path: str | None) -> str:
    if not path:
        return "unknown"
    normalized = path.lower()
    for marker in ("safetensors", "gguf", "onnx"):
        if f".{marker}" in normalized or normalized.endswith(marker):
            return marker
    filename = normalized.rsplit("/", maxsplit=1)[-1]
    if "." not in filename:
        return "unknown"
    return filename.rsplit(".", maxsplit=1)[-1] or "unknown"


def _map_model_file(sibling: Any) -> dict[str, Any]:
    path = getattr(sibling, "rfilename", None)
    file_details = {
        "path": path,
        "size": getattr(sibling, "size", None),
        "file_type": _file_type(path),
    }
    _add_optional(file_details, "blob_id", getattr(sibling, "blob_id", None))
    _add_optional(file_details, "lfs", getattr(sibling, "lfs", None))
    return file_details


def _optional_model_detail_fields(info: Any) -> dict[str, Any]:
    return {
        "author": getattr(info, "author", None),
        "pipeline_tag": getattr(info, "pipeline_tag", None),
        "library_name": getattr(info, "library_name", None),
        "gated": getattr(info, "gated", None),
        "private": getattr(info, "private", None),
        "disabled": getattr(info, "disabled", None),
        "created_at": _first_attr(info, "created_at", "createdAt"),
        "last_modified": _first_attr(info, "last_modified", "lastModified"),
        "used_storage": _first_attr(info, "used_storage", "usedStorage"),
        "card_data": _first_attr(info, "card_data", "cardData"),
        "config": getattr(info, "config", None),
        "safetensors": getattr(info, "safetensors", None),
        "model_index": _first_attr(info, "model_index", "modelIndex"),
        "transformers_info": _first_attr(info, "transformers_info", "transformersInfo"),
    }


def _map_model_details(info: Any) -> dict[str, Any]:
    result = {
        "source_id": info.id,
        "name": info.id.split("/")[-1] if info.id else "",
        "sha": getattr(info, "sha", None),
        "downloads": getattr(info, "downloads", None),
        "likes": getattr(info, "likes", None),
        "tags": getattr(info, "tags", []) or [],
        "files": [
            _map_model_file(sibling)
            for sibling in (getattr(info, "siblings", None) or [])
        ],
    }
    for key, value in _optional_model_detail_fields(info).items():
        _add_optional(result, key, value)
    return result


def discover_hf_models(
    *,
    database_url: str,
    query: str,
    task: str = "text-generation",
    sort: str = "downloads",
    limit: int = 10,
    offset: int = 0,
    token: str | None = None,
) -> list[dict[str, Any]]:
    assert_internet_allowed(database_url, "Model discovery")

    from huggingface_hub import HfApi

    api = HfApi(token=token or None)
    models = api.list_models(
        search=query or None,
        filter=task if task else None,
        sort=sort,
        limit=offset + limit,
    )
    results: list[dict[str, Any]] = []
    for model in islice(models, offset, offset + limit):
        results.append(
            {
                "source_id": model.id,
                "name": model.id.split("/")[-1] if model.id else "",
                "downloads": getattr(model, "downloads", None),
                "likes": getattr(model, "likes", None),
                "tags": getattr(model, "tags", []) or [],
                "provider": "huggingface",
            }
        )
    return results


def get_hf_model_details(source_id: str, *, database_url: str, token: str | None = None) -> dict[str, Any]:
    assert_internet_allowed(database_url, "Model discovery")

    from huggingface_hub import HfApi

    api = HfApi(token=token or None)
    info = api.model_info(repo_id=source_id, files_metadata=True)
    return _map_model_details(info)
