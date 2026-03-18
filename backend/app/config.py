from __future__ import annotations

import os
from dataclasses import dataclass

RUNTIME_PROFILES = {"online", "offline", "air_gapped"}
DEFAULT_RUNTIME_PROFILE = "offline"

DEFAULT_FRONTEND_URL = "http://frontend:3000"
DEFAULT_BACKEND_URL = "http://backend:5000"
DEFAULT_LLM_URL = "http://llm:8000"
DEFAULT_LLM_RUNTIME_URL = "http://llm_runtime:8000"
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = 60
DEFAULT_AGENT_ENGINE_URL = "http://agent_engine:7000"
DEFAULT_AGENT_ENGINE_SERVICE_TOKEN = "dev-agent-engine-token"
DEFAULT_SANDBOX_URL = "http://sandbox:6000"
DEFAULT_MCP_GATEWAY_URL = ""
DEFAULT_KWS_URL = "http://kws:10400"
DEFAULT_WEAVIATE_URL = "http://weaviate:8080"
DEFAULT_LLAMA_CPP_URL = ""
DEFAULT_QDRANT_URL = ""
DEFAULT_PRODUCT_RAG_INDEX = "knowledge_base"
DEFAULT_PRODUCT_RAG_TOP_K = 5


@dataclass(frozen=True)
class BackendRuntimeConfig:
    frontend_url: str = DEFAULT_FRONTEND_URL
    backend_url: str = DEFAULT_BACKEND_URL
    llm_url: str = DEFAULT_LLM_URL
    llm_runtime_url: str = DEFAULT_LLM_RUNTIME_URL
    agent_engine_url: str = DEFAULT_AGENT_ENGINE_URL
    agent_engine_service_token: str = DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
    sandbox_url: str = DEFAULT_SANDBOX_URL
    mcp_gateway_url: str = DEFAULT_MCP_GATEWAY_URL
    kws_url: str = DEFAULT_KWS_URL
    weaviate_url: str = DEFAULT_WEAVIATE_URL
    llama_cpp_url: str = DEFAULT_LLAMA_CPP_URL
    qdrant_url: str = DEFAULT_QDRANT_URL
    runtime_profile_override: str | None = None
    kws_detection_threshold: float = 0.5
    kws_cooldown_ms: int = 2_000


@dataclass(frozen=True)
class AuthConfig:
    database_url: str
    jwt_secret: str
    model_credentials_encryption_key: str
    jwt_algorithm: str
    access_token_ttl_seconds: int
    allow_self_register: bool
    bootstrap_superadmin_email: str
    bootstrap_superadmin_username: str
    bootstrap_superadmin_password: str
    flask_env: str
    model_storage_root: str = "/models/llm"
    model_download_max_workers: int = 2
    model_download_stale_seconds: int = 900
    model_download_allow_patterns_default: str = ""
    model_download_ignore_patterns_default: str = ""
    hf_token: str = ""
    agent_engine_url: str = DEFAULT_AGENT_ENGINE_URL
    agent_engine_service_token: str = DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
    agent_execution_via_engine: bool = True
    agent_execution_fallback: bool = False
    frontend_url: str = DEFAULT_FRONTEND_URL
    backend_url: str = DEFAULT_BACKEND_URL
    llm_url: str = DEFAULT_LLM_URL
    llm_runtime_url: str = DEFAULT_LLM_RUNTIME_URL
    llm_request_timeout_seconds: int = DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS
    sandbox_url: str = DEFAULT_SANDBOX_URL
    mcp_gateway_url: str = DEFAULT_MCP_GATEWAY_URL
    kws_url: str = DEFAULT_KWS_URL
    weaviate_url: str = DEFAULT_WEAVIATE_URL
    llama_cpp_url: str = DEFAULT_LLAMA_CPP_URL
    qdrant_url: str = DEFAULT_QDRANT_URL
    product_rag_index: str = DEFAULT_PRODUCT_RAG_INDEX
    product_rag_top_k: int = DEFAULT_PRODUCT_RAG_TOP_K
    runtime_profile_override: str | None = None
    kws_detection_threshold: float = 0.5
    kws_cooldown_ms: int = 2_000


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


def _get_nonnegative_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_runtime_profile_override_env() -> str | None:
    value = os.getenv("VANESSA_RUNTIME_PROFILE")
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in RUNTIME_PROFILES:
        return normalized
    return None


def get_auth_config() -> AuthConfig:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")

    flask_env = os.getenv("FLASK_ENV", "development").strip().lower() or "development"

    jwt_secret = os.getenv("AUTH_JWT_SECRET", "").strip()
    if not jwt_secret:
        if flask_env == "development":
            jwt_secret = "insecure-dev-only-secret"
            print("[WARN] AUTH_JWT_SECRET not set; using insecure development fallback.")
        else:
            raise RuntimeError("AUTH_JWT_SECRET must be set outside development")

    return AuthConfig(
        database_url=database_url,
        jwt_secret=jwt_secret,
        model_credentials_encryption_key=(
            os.getenv("MODEL_CREDENTIALS_ENCRYPTION_KEY", "").strip() or jwt_secret
        ),
        jwt_algorithm=os.getenv("AUTH_JWT_ALGORITHM", "HS256").strip() or "HS256",
        access_token_ttl_seconds=_get_int_env("AUTH_ACCESS_TOKEN_TTL_SECONDS", 28_800),
        allow_self_register=_get_bool_env("AUTH_ALLOW_SELF_REGISTER", True),
        bootstrap_superadmin_email=os.getenv("AUTH_BOOTSTRAP_SUPERADMIN_EMAIL", "").strip(),
        bootstrap_superadmin_username=os.getenv("AUTH_BOOTSTRAP_SUPERADMIN_USERNAME", "").strip(),
        bootstrap_superadmin_password=os.getenv("AUTH_BOOTSTRAP_SUPERADMIN_PASSWORD", ""),
        flask_env=flask_env,
        model_storage_root=os.getenv("MODEL_STORAGE_ROOT", "/models/llm").strip() or "/models/llm",
        model_download_max_workers=_get_int_env("MODEL_DOWNLOAD_MAX_WORKERS", 2),
        model_download_stale_seconds=_get_int_env("MODEL_DOWNLOAD_STALE_SECONDS", 900),
        model_download_allow_patterns_default=os.getenv("MODEL_DOWNLOAD_ALLOW_PATTERNS_DEFAULT", "").strip(),
        model_download_ignore_patterns_default=os.getenv("MODEL_DOWNLOAD_IGNORE_PATTERNS_DEFAULT", "").strip(),
        hf_token=os.getenv("HF_TOKEN", "").strip(),
        agent_engine_url=os.getenv("AGENT_ENGINE_URL", DEFAULT_AGENT_ENGINE_URL).strip() or DEFAULT_AGENT_ENGINE_URL,
        agent_engine_service_token=os.getenv("AGENT_ENGINE_SERVICE_TOKEN", DEFAULT_AGENT_ENGINE_SERVICE_TOKEN).strip()
        or DEFAULT_AGENT_ENGINE_SERVICE_TOKEN,
        agent_execution_via_engine=_get_bool_env("AGENT_EXECUTION_VIA_ENGINE", True),
        agent_execution_fallback=_get_bool_env("AGENT_EXECUTION_FALLBACK", False),
        frontend_url=os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL).strip() or DEFAULT_FRONTEND_URL,
        backend_url=os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip() or DEFAULT_BACKEND_URL,
        llm_url=os.getenv("LLM_URL", DEFAULT_LLM_URL).strip() or DEFAULT_LLM_URL,
        llm_runtime_url=os.getenv("LLM_RUNTIME_URL", DEFAULT_LLM_RUNTIME_URL).strip() or DEFAULT_LLM_RUNTIME_URL,
        llm_request_timeout_seconds=_get_int_env("LLM_REQUEST_TIMEOUT_SECONDS", DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS),
        sandbox_url=os.getenv("SANDBOX_URL", DEFAULT_SANDBOX_URL).strip() or DEFAULT_SANDBOX_URL,
        mcp_gateway_url=os.getenv("MCP_GATEWAY_URL", DEFAULT_MCP_GATEWAY_URL).strip(),
        kws_url=os.getenv("KWS_URL", DEFAULT_KWS_URL).strip() or DEFAULT_KWS_URL,
        weaviate_url=os.getenv("WEAVIATE_URL", DEFAULT_WEAVIATE_URL).strip() or DEFAULT_WEAVIATE_URL,
        llama_cpp_url=os.getenv("LLAMA_CPP_URL", DEFAULT_LLAMA_CPP_URL).strip(),
        qdrant_url=os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL).strip(),
        product_rag_index=os.getenv("PRODUCT_RAG_INDEX", DEFAULT_PRODUCT_RAG_INDEX).strip() or DEFAULT_PRODUCT_RAG_INDEX,
        product_rag_top_k=_get_int_env("PRODUCT_RAG_TOP_K", DEFAULT_PRODUCT_RAG_TOP_K),
        runtime_profile_override=_get_runtime_profile_override_env(),
        kws_detection_threshold=_get_float_env("KWS_DETECTION_THRESHOLD", 0.5),
        kws_cooldown_ms=_get_nonnegative_int_env("KWS_COOLDOWN_MS", 2_000),
    )


def get_backend_runtime_config() -> BackendRuntimeConfig:
    return BackendRuntimeConfig(
        frontend_url=os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL).strip() or DEFAULT_FRONTEND_URL,
        backend_url=os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip() or DEFAULT_BACKEND_URL,
        llm_url=os.getenv("LLM_URL", DEFAULT_LLM_URL).strip() or DEFAULT_LLM_URL,
        llm_runtime_url=os.getenv("LLM_RUNTIME_URL", DEFAULT_LLM_RUNTIME_URL).strip() or DEFAULT_LLM_RUNTIME_URL,
        agent_engine_url=os.getenv("AGENT_ENGINE_URL", DEFAULT_AGENT_ENGINE_URL).strip() or DEFAULT_AGENT_ENGINE_URL,
        agent_engine_service_token=os.getenv("AGENT_ENGINE_SERVICE_TOKEN", DEFAULT_AGENT_ENGINE_SERVICE_TOKEN).strip()
        or DEFAULT_AGENT_ENGINE_SERVICE_TOKEN,
        sandbox_url=os.getenv("SANDBOX_URL", DEFAULT_SANDBOX_URL).strip() or DEFAULT_SANDBOX_URL,
        mcp_gateway_url=os.getenv("MCP_GATEWAY_URL", DEFAULT_MCP_GATEWAY_URL).strip(),
        kws_url=os.getenv("KWS_URL", DEFAULT_KWS_URL).strip() or DEFAULT_KWS_URL,
        weaviate_url=os.getenv("WEAVIATE_URL", DEFAULT_WEAVIATE_URL).strip() or DEFAULT_WEAVIATE_URL,
        llama_cpp_url=os.getenv("LLAMA_CPP_URL", DEFAULT_LLAMA_CPP_URL).strip(),
        qdrant_url=os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL).strip(),
        runtime_profile_override=_get_runtime_profile_override_env(),
        kws_detection_threshold=_get_float_env("KWS_DETECTION_THRESHOLD", 0.5),
        kws_cooldown_ms=_get_nonnegative_int_env("KWS_COOLDOWN_MS", 2_000),
    )
