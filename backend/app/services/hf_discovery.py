from __future__ import annotations

from typing import Any

from .connectivity_policy import assert_internet_allowed

def discover_hf_models(
    *,
    database_url: str,
    query: str,
    task: str = "text-generation",
    sort: str = "downloads",
    limit: int = 10,
    token: str | None = None,
) -> list[dict[str, Any]]:
    assert_internet_allowed(database_url, "Model discovery")

    from huggingface_hub import HfApi

    api = HfApi(token=token or None)
    models = api.list_models(
        search=query or None,
        filter=task if task else None,
        sort=sort,
        direction=-1,
        limit=limit,
    )
    results: list[dict[str, Any]] = []
    for model in models:
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
    return {
        "source_id": info.id,
        "name": info.id.split("/")[-1] if info.id else "",
        "sha": getattr(info, "sha", None),
        "downloads": getattr(info, "downloads", None),
        "likes": getattr(info, "likes", None),
        "tags": getattr(info, "tags", []) or [],
        "files": [
            {
                "path": sibling.rfilename,
                "size": getattr(sibling, "size", None),
            }
            for sibling in (getattr(info, "siblings", None) or [])
        ],
    }
