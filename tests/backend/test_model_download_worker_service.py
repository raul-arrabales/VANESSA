from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.config import AuthConfig  # noqa: E402
from app.services import model_download_worker  # noqa: E402


def _config() -> AuthConfig:
    return AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
        model_storage_root="/models/llm",
        model_download_max_workers=2,
        model_download_stale_seconds=900,
        model_download_allow_patterns_default="",
        model_download_ignore_patterns_default="",
        hf_token="",
    )


def test_download_worker_loop_processes_job_without_app_module(monkeypatch):
    cfg = _config()
    calls: dict[str, object] = {}

    jobs = [
        {
            "id": "job-1",
            "provider": "huggingface",
            "source_id": "org/model",
            "target_dir": "/models/llm/org--model",
        }
    ]

    def _claim(_db: str):
        if jobs:
            return jobs.pop(0)
        raise KeyboardInterrupt

    monkeypatch.setattr(model_download_worker, "get_auth_config", lambda: cfg)
    monkeypatch.setattr(model_download_worker, "claim_next_queued_job", _claim)
    monkeypatch.setattr(model_download_worker, "get_model_catalog_item", lambda _db, _model_id: None)
    monkeypatch.setattr(model_download_worker, "download_from_huggingface", lambda **kwargs: "/models/llm/org--model")

    def _upsert(_db: str, **kwargs):
        calls["upsert"] = kwargs
        return kwargs

    monkeypatch.setattr(model_download_worker, "upsert_model_catalog_item", _upsert)
    monkeypatch.setattr(model_download_worker, "mark_job_succeeded", lambda _db, *, job_id, model_id: calls.update({"succeeded": (job_id, model_id)}))
    monkeypatch.setattr(model_download_worker, "mark_job_failed", lambda *_args, **_kwargs: calls.update({"failed": True}))
    monkeypatch.setattr(model_download_worker.time, "sleep", lambda _secs: None)

    try:
        model_download_worker.download_worker_loop()
    except KeyboardInterrupt:
        pass

    assert "upsert" in calls
    assert calls.get("succeeded") == ("job-1", "org--model")
    assert "failed" not in calls


def test_ensure_download_worker_started_spawns_expected_workers(monkeypatch):
    cfg = _config()
    started: list[str] = []

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            self._target = target
            self.name = name
            self.daemon = daemon

        def start(self):
            started.append(self.name)

    monkeypatch.setattr(model_download_worker, "get_auth_config", lambda: cfg)
    monkeypatch.setattr(model_download_worker, "reconcile_stale_running_jobs", lambda _db, *, stale_after_seconds: None)
    monkeypatch.setattr(model_download_worker.threading, "Thread", FakeThread)
    monkeypatch.setattr(model_download_worker, "_download_worker_started", False)

    model_download_worker.ensure_download_worker_started()

    assert started == ["model-download-worker-1", "model-download-worker-2"]
