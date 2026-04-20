from __future__ import annotations

import logging
import threading
import time

from ..config import get_auth_config
from ..repositories.context_management import (
    claim_next_queued_sync_run,
    reconcile_stale_sync_runs,
)
from .context_management_documents import perform_knowledge_base_resync_run
from .context_management_sources import perform_knowledge_source_sync_run

_SYNC_POLL_SECONDS = 1.0
_sync_worker_started = False
_sync_worker_lock = threading.Lock()

logger = logging.getLogger(__name__)


def sync_worker_loop() -> None:
    while True:
        try:
            config = get_auth_config()
            run = claim_next_queued_sync_run(config.database_url)
            if run is None:
                time.sleep(_SYNC_POLL_SECONDS)
                continue

            operation_type = str(run.get("operation_type") or "").strip().lower()
            if operation_type == "source_sync":
                perform_knowledge_source_sync_run(config.database_url, config=config, run=run)
                continue
            if operation_type == "knowledge_resync":
                perform_knowledge_base_resync_run(config.database_url, config=config, run=run)
                continue
            logger.error("Unknown knowledge sync operation type: %s", operation_type)
        except Exception as exc:  # noqa: BLE001
            logger.error("Knowledge sync worker loop error: %s", exc)
            time.sleep(_SYNC_POLL_SECONDS)


def ensure_knowledge_sync_worker_started() -> None:
    global _sync_worker_started
    if _sync_worker_started:
        return

    with _sync_worker_lock:
        if _sync_worker_started:
            return

        config = get_auth_config()
        reconcile_stale_sync_runs(
            config.database_url,
            stale_after_seconds=config.knowledge_sync_stale_seconds,
        )

        for index in range(config.knowledge_sync_max_workers):
            worker = threading.Thread(
                target=sync_worker_loop,
                name=f"knowledge-sync-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
        _sync_worker_started = True
