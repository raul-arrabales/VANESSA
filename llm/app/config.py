from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class LLMConfig:
    routing_mode: str
    local_base_url: str
    local_upstream_model: str
    enable_hf_router: bool
    hf_base_url: str
    hf_token: str
    hf_upstream_model: str
    enable_openai: bool
    openai_base_url: str
    openai_api_key: str
    openai_upstream_model: str
    enable_cloud_failover: bool
    request_timeout_seconds: int
    enable_dummy_model: bool


def load_llm_config() -> LLMConfig:
    local_model_path = (
        os.getenv("LLM_LOCAL_MODEL_PATH", "/models/llm/Qwen--Qwen2.5-0.5B-Instruct").strip()
        or "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"
    )
    local_upstream_model = (
        os.getenv("LLM_LOCAL_UPSTREAM_MODEL", "").strip()
        or local_model_path
    )
    return LLMConfig(
        routing_mode=os.getenv("LLM_ROUTING_MODE", "local_only").strip().lower() or "local_only",
        local_base_url=os.getenv("LLM_LOCAL_BASE_URL", "http://llm_runtime:8000/v1").strip()
        or "http://llm_runtime:8000/v1",
        local_upstream_model=local_upstream_model,
        enable_hf_router=_get_bool_env("LLM_ENABLE_HF_ROUTER", False),
        hf_base_url=os.getenv("LLM_HF_BASE_URL", "https://router.huggingface.co/v1").strip()
        or "https://router.huggingface.co/v1",
        hf_token=os.getenv("HF_TOKEN", "").strip(),
        hf_upstream_model=os.getenv("LLM_HF_UPSTREAM_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
        or "meta-llama/Llama-3.1-8B-Instruct",
        enable_openai=_get_bool_env("LLM_ENABLE_OPENAI", False),
        openai_base_url=os.getenv("LLM_OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        or "https://api.openai.com/v1",
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_upstream_model=os.getenv("LLM_OPENAI_UPSTREAM_MODEL", "gpt-4o-mini").strip()
        or "gpt-4o-mini",
        enable_cloud_failover=_get_bool_env("LLM_ENABLE_CLOUD_FAILOVER", False),
        request_timeout_seconds=_get_int_env("LLM_REQUEST_TIMEOUT_SECONDS", 60),
        enable_dummy_model=_get_bool_env("LLM_ENABLE_DUMMY_MODEL", True),
    )
