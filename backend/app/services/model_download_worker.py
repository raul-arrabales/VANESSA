from __future__ import annotations

import threading
import time

_DOWNLOAD_POLL_SECONDS = 1.0
_download_worker_started = False
_download_worker_lock = threading.Lock()


def _m():
    import app.app as backend_app_module

    return backend_app_module


def download_worker_loop() -> None:
    while True:
        try:
            m = _m()
            config = m._get_config()
            job = m.claim_next_queued_job(config.database_url)
            if job is None:
                time.sleep(_DOWNLOAD_POLL_SECONDS)
                continue

            allow_patterns = m._parse_patterns(config.model_download_allow_patterns_default)
            ignore_patterns = m._parse_patterns(config.model_download_ignore_patterns_default)
            source_id = str(job.get("source_id", ""))
            provider = str(job.get("provider", "huggingface"))
            model_id = m._model_id_from_source(source_id)
            model_name = source_id.split("/")[-1] if "/" in source_id else source_id
            existing_model = m.get_model_catalog_item(config.database_url, model_id)
            if existing_model is not None:
                metadata = (
                    existing_model.get("metadata")
                    if isinstance(existing_model.get("metadata"), dict)
                    else {}
                )
                allow_patterns = (
                    m._parse_patterns(metadata.get("allow_patterns")) or allow_patterns
                )
                ignore_patterns = (
                    m._parse_patterns(metadata.get("ignore_patterns")) or ignore_patterns
                )

            try:
                local_path = m.download_from_huggingface(
                    source_id=source_id,
                    storage_root=config.model_storage_root,
                    token=config.hf_token,
                    allow_patterns=allow_patterns,
                    ignore_patterns=ignore_patterns,
                )
            except Exception as exc:  # noqa: BLE001
                m.upsert_model_catalog_item(
                    config.database_url,
                    model_id=model_id,
                    name=model_name,
                    provider=provider,
                    source_id=source_id,
                    local_path=str(job.get("target_dir", "")) or None,
                    status="failed",
                    metadata={"source": "huggingface", "error": str(exc)},
                    updated_by_user_id=None,
                )
                m.mark_job_failed(
                    config.database_url,
                    job_id=str(job["id"]),
                    error_message=str(exc)[:2000],
                )
                continue

            m.upsert_model_catalog_item(
                config.database_url,
                model_id=model_id,
                name=model_name,
                provider=provider,
                source_id=source_id,
                local_path=local_path,
                status="available",
                metadata={"source": "huggingface"},
                updated_by_user_id=None,
            )
            m.mark_job_succeeded(
                config.database_url,
                job_id=str(job["id"]),
                model_id=model_id,
            )
        except Exception as exc:  # noqa: BLE001
            _m().app.logger.error("Model download worker loop error: %s", exc)
            time.sleep(_DOWNLOAD_POLL_SECONDS)


def ensure_download_worker_started() -> None:
    global _download_worker_started
    if _download_worker_started:
        return

    with _download_worker_lock:
        if _download_worker_started:
            return
        m = _m()
        config = m._get_config()
        m.reconcile_stale_running_jobs(
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
