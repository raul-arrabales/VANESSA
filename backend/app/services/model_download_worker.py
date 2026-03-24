from __future__ import annotations

import logging
import threading
import time

from ..config import get_auth_config
from ..repositories import modelops as modelops_repo
from ..repositories.model_download_jobs import (
    claim_next_queued_job,
    mark_job_failed,
    mark_job_succeeded,
    reconcile_stale_running_jobs,
)
from ..services.model_support import model_id_from_source, parse_patterns
from ..services.model_downloader import download_from_huggingface

_DOWNLOAD_POLL_SECONDS = 1.0
_download_worker_started = False
_download_worker_lock = threading.Lock()


logger = logging.getLogger(__name__)


def get_model_catalog_item(database_url: str, model_id: str) -> dict[str, object] | None:
    return modelops_repo.get_model(database_url, model_id)


def upsert_model_catalog_item(database_url: str, **kwargs):
    return modelops_repo.upsert_model_record(database_url, **kwargs)


def download_worker_loop() -> None:
    while True:
        try:
            config = get_auth_config()
            job = claim_next_queued_job(config.database_url)
            if job is None:
                time.sleep(_DOWNLOAD_POLL_SECONDS)
                continue

            allow_patterns = parse_patterns(config.model_download_allow_patterns_default)
            ignore_patterns = parse_patterns(config.model_download_ignore_patterns_default)
            source_id = str(job.get("source_id", ""))
            provider = str(job.get("provider", "huggingface"))
            model_id = model_id_from_source(source_id)
            model_name = source_id.split("/")[-1] if "/" in source_id else source_id
            existing_model = get_model_catalog_item(config.database_url, model_id)
            if existing_model is not None:
                metadata = (
                    existing_model.get("metadata")
                    if isinstance(existing_model.get("metadata"), dict)
                    else {}
                )
                allow_patterns = parse_patterns(metadata.get("allow_patterns")) or allow_patterns
                ignore_patterns = parse_patterns(metadata.get("ignore_patterns")) or ignore_patterns

            try:
                local_path = download_from_huggingface(
                    database_url=config.database_url,
                    source_id=source_id,
                    storage_root=config.model_storage_root,
                    token=config.hf_token,
                    allow_patterns=allow_patterns,
                    ignore_patterns=ignore_patterns,
                )
            except Exception as exc:  # noqa: BLE001
                upsert_model_catalog_item(
                    config.database_url,
                    model_id=model_id,
                    node_id=config.modelops_node_id,
                    name=model_name,
                    provider=provider,
                    task_key=str((existing_model or {}).get("task_key") or modelops_repo.TASK_LLM),
                    category=str((existing_model or {}).get("category") or modelops_repo.infer_category(str((existing_model or {}).get("task_key") or modelops_repo.TASK_LLM))),
                    backend_kind="local",
                    source_kind="hf_import",
                    availability="offline_ready",
                    visibility_scope="platform",
                    owner_type=modelops_repo.OWNER_PLATFORM,
                    owner_user_id=None,
                    provider_model_id=None,
                    credential_id=None,
                    source_id=source_id,
                    local_path=str(job.get("target_dir", "")) or None,
                    status="failed",
                    lifecycle_state=modelops_repo.LIFECYCLE_CREATED,
                    metadata={"source": "huggingface", "error": str(exc)},
                    comment=None,
                    model_size_billion=None,
                    created_by_user_id=None,
                    registered_by_user_id=None,
                )
                mark_job_failed(
                    config.database_url,
                    job_id=str(job["id"]),
                    error_message=str(exc)[:2000],
                )
                continue

            upsert_model_catalog_item(
                config.database_url,
                model_id=model_id,
                node_id=config.modelops_node_id,
                name=model_name,
                provider=provider,
                task_key=str((existing_model or {}).get("task_key") or modelops_repo.TASK_LLM),
                category=str((existing_model or {}).get("category") or modelops_repo.infer_category(str((existing_model or {}).get("task_key") or modelops_repo.TASK_LLM))),
                backend_kind="local",
                source_kind="hf_import",
                availability="offline_ready",
                visibility_scope="platform",
                owner_type=modelops_repo.OWNER_PLATFORM,
                owner_user_id=None,
                provider_model_id=None,
                credential_id=None,
                source_id=source_id,
                local_path=local_path,
                status="available",
                lifecycle_state=modelops_repo.LIFECYCLE_REGISTERED,
                metadata={"source": "huggingface"},
                comment=None,
                model_size_billion=None,
                created_by_user_id=None,
                registered_by_user_id=None,
            )
            mark_job_succeeded(
                config.database_url,
                job_id=str(job["id"]),
                model_id=model_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Model download worker loop error: %s", exc)
            time.sleep(_DOWNLOAD_POLL_SECONDS)


def ensure_download_worker_started() -> None:
    global _download_worker_started
    if _download_worker_started:
        return

    with _download_worker_lock:
        if _download_worker_started:
            return

        config = get_auth_config()
        reconcile_stale_running_jobs(
            config.database_url,
            stale_after_seconds=config.model_download_stale_seconds,
        )

        for index in range(config.model_download_max_workers):
            worker = threading.Thread(
                target=download_worker_loop,
                name=f"model-download-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
        _download_worker_started = True
