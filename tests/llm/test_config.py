from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_CONFIG_PATH = PROJECT_ROOT / "llm" / "app" / "config.py"


def _load_llm_config_fn():
    spec = importlib.util.spec_from_file_location("vanessa_llm_config", LLM_CONFIG_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_llm_config


def test_local_upstream_model_defaults_to_local_model_path(monkeypatch) -> None:
    load_llm_config = _load_llm_config_fn()
    monkeypatch.delenv("LLM_LOCAL_UPSTREAM_MODEL", raising=False)
    monkeypatch.setenv("LLM_LOCAL_MODEL_PATH", "/models/llm/Qwen--Qwen2.5-0.5B-Instruct")

    config = load_llm_config()

    assert config.local_upstream_model == "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"


def test_local_upstream_model_env_override_wins(monkeypatch) -> None:
    load_llm_config = _load_llm_config_fn()
    monkeypatch.setenv("LLM_LOCAL_MODEL_PATH", "/models/llm/Qwen--Qwen2.5-0.5B-Instruct")
    monkeypatch.setenv("LLM_LOCAL_UPSTREAM_MODEL", "custom-model-id")

    config = load_llm_config()

    assert config.local_upstream_model == "custom-model-id"
