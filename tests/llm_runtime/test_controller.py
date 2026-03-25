from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_runtime.runtime_app.config import RuntimeControllerConfig, load_runtime_controller_config
from llm_runtime.runtime_app import controller as runtime_controller


class _FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        self.returncode = 0
        return 0

    def kill(self) -> None:
        self.returncode = -9


def _config(model_root: Path) -> RuntimeControllerConfig:
    return RuntimeControllerConfig(
        capability="embeddings",
        service_name="llm_runtime_embeddings",
        listen_host="127.0.0.1",
        listen_port=8000,
        child_host="127.0.0.1",
        child_port=8001,
        dtype="float",
        device="cpu",
        model_root=model_root,
        startup_local_path=None,
        startup_runtime_model_id=None,
        startup_display_name=None,
        additional_args=(),
        load_timeout_seconds=2,
        health_poll_interval_seconds=0.01,
    )


def test_runtime_controller_loads_and_unloads_model(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_root = Path(tmp_dir)
        model_path = model_root / "sentence-transformers--all-MiniLM-L6-v2"
        model_path.mkdir(parents=True)
        controller = runtime_controller.RuntimeController(_config(model_root))

        monkeypatch.setattr(runtime_controller.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess())
        monkeypatch.setattr(
            runtime_controller,
            "_http_json_request",
            lambda *args, **kwargs: (
                {"data": [{"id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2"}]},
                200,
            ),
        )

        controller.load_model(
            runtime_model_id="/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            local_path=str(model_path),
            managed_model_id="model-1",
            display_name="MiniLM",
        )

        deadline = time.time() + 1
        while time.time() < deadline:
            state = controller.get_state()
            if state["load_state"] == "loaded":
                break
            time.sleep(0.02)

        state = controller.get_state()
        assert state["load_state"] == "loaded"
        assert state["runtime_model_id"] == "/models/llm/sentence-transformers--all-MiniLM-L6-v2"

        empty_state = controller.unload_model()
        assert empty_state["load_state"] == "empty"
        assert empty_state["runtime_model_id"] is None


def test_runtime_controller_config_uses_split_startup_paths(monkeypatch):
    monkeypatch.setenv("LLM_RUNTIME_CAPABILITY", "embeddings")
    monkeypatch.setenv("LLM_EMBEDDINGS_LOCAL_MODEL_PATH", "/models/llm/embeddings-model")
    monkeypatch.setenv("LLM_LOCAL_MODEL_PATH", "/models/llm/fallback-model")
    monkeypatch.setenv("LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL", "embeddings-runtime-id")
    monkeypatch.setenv("LLM_LOCAL_UPSTREAM_MODEL", "inference-runtime-id")

    config = load_runtime_controller_config()

    assert config.capability == "embeddings"
    assert config.startup_local_path == "/models/llm/embeddings-model"
    assert config.startup_runtime_model_id == "embeddings-runtime-id"


def test_embeddings_runtime_config_stays_empty_without_dedicated_startup_env(monkeypatch):
    monkeypatch.setenv("LLM_RUNTIME_CAPABILITY", "embeddings")
    monkeypatch.setenv("LLM_LOCAL_MODEL_PATH", "/models/llm/fallback-model")
    monkeypatch.setenv("LLM_LOCAL_UPSTREAM_MODEL", "inference-runtime-id")
    monkeypatch.delenv("LLM_EMBEDDINGS_LOCAL_MODEL_PATH", raising=False)
    monkeypatch.delenv("LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL", raising=False)

    config = load_runtime_controller_config()

    assert config.capability == "embeddings"
    assert config.startup_local_path is None
    assert config.startup_runtime_model_id is None


def test_inference_runtime_config_keeps_generic_local_fallback(monkeypatch):
    monkeypatch.setenv("LLM_RUNTIME_CAPABILITY", "llm_inference")
    monkeypatch.setenv("LLM_LOCAL_MODEL_PATH", "/models/llm/fallback-model")
    monkeypatch.setenv("LLM_LOCAL_UPSTREAM_MODEL", "inference-runtime-id")
    monkeypatch.delenv("LLM_INFERENCE_LOCAL_MODEL_PATH", raising=False)

    config = load_runtime_controller_config()

    assert config.capability == "llm_inference"
    assert config.startup_local_path == "/models/llm/fallback-model"
    assert config.startup_runtime_model_id == "inference-runtime-id"
