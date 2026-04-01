from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..repositories import modelops as modelops_repo
from ..repositories import platform_control_plane as platform_repo
from .platform_types import PlatformControlPlaneError

CHUNKING_STRATEGY_FIXED_LENGTH = "fixed_length"
CHUNKING_UNIT_TOKENS = "tokens"
DEFAULT_CHUNK_LENGTH = 300
DEFAULT_CHUNK_OVERLAP = 60
SUPPORTED_CHUNKING_STRATEGIES = {CHUNKING_STRATEGY_FIXED_LENGTH}


class TextTokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, token_ids: list[int]) -> str:
        ...


@dataclass(frozen=True)
class FixedLengthChunkingConfig:
    unit: str
    chunk_length: int
    chunk_overlap: int


@dataclass(frozen=True)
class KnowledgeBaseChunking:
    strategy: str
    config: FixedLengthChunkingConfig


@dataclass(frozen=True)
class _TransformersTextTokenizer:
    tokenizer: Any

    def encode(self, text: str) -> list[int]:
        return list(self.tokenizer.encode(text, add_special_tokens=False))

    def decode(self, token_ids: list[int]) -> str:
        return str(
            self.tokenizer.decode(
                token_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )
        )


@dataclass(frozen=True)
class _TiktokenTextTokenizer:
    encoding: Any

    def encode(self, text: str) -> list[int]:
        return list(self.encoding.encode(text))

    def decode(self, token_ids: list[int]) -> str:
        return str(self.encoding.decode(token_ids))


def default_chunking_payload() -> dict[str, Any]:
    return {
        "strategy": CHUNKING_STRATEGY_FIXED_LENGTH,
        "config": {
            "unit": CHUNKING_UNIT_TOKENS,
            "chunk_length": DEFAULT_CHUNK_LENGTH,
            "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        },
    }


def normalize_knowledge_base_chunking(
    payload: dict[str, Any],
    *,
    is_create: bool,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    if not is_create:
        has_chunking_update = any(key in payload for key in {"chunking", "chunking_strategy", "chunking_config_json"})
        if not has_chunking_update:
            return serialize_knowledge_base_chunking(existing or {})
        if int((existing or {}).get("document_count") or 0) > 0:
            raise PlatformControlPlaneError(
                "chunking_immutable",
                "chunking cannot be changed after documents have been ingested",
                status_code=409,
            )
        raw_chunking = payload.get("chunking")
        if not isinstance(raw_chunking, dict):
            raise PlatformControlPlaneError(
                "invalid_chunking",
                "chunking is required",
                status_code=400,
            )
        strategy = str(raw_chunking.get("strategy") or "").strip().lower()
        if strategy not in SUPPORTED_CHUNKING_STRATEGIES:
            raise PlatformControlPlaneError(
                "invalid_chunking_strategy",
                "chunking.strategy is unsupported",
                status_code=400,
            )
        return {
            "strategy": strategy,
            "config": _normalize_fixed_length_chunking_config(raw_chunking.get("config")),
        }

    raw_chunking = payload.get("chunking")
    if not isinstance(raw_chunking, dict):
        raise PlatformControlPlaneError(
            "invalid_chunking",
            "chunking is required",
            status_code=400,
        )
    strategy = str(raw_chunking.get("strategy") or "").strip().lower()
    if strategy not in SUPPORTED_CHUNKING_STRATEGIES:
        raise PlatformControlPlaneError(
            "invalid_chunking_strategy",
            "chunking.strategy is unsupported",
            status_code=400,
        )
    if strategy == CHUNKING_STRATEGY_FIXED_LENGTH:
        return {
            "strategy": strategy,
            "config": _normalize_fixed_length_chunking_config(raw_chunking.get("config")),
        }
    raise PlatformControlPlaneError(
        "invalid_chunking_strategy",
        "chunking.strategy is unsupported",
        status_code=400,
    )


def serialize_knowledge_base_chunking(row: dict[str, Any]) -> dict[str, Any]:
    raw_strategy = str(row.get("chunking_strategy") or CHUNKING_STRATEGY_FIXED_LENGTH).strip().lower()
    raw_config = dict(row.get("chunking_config_json") or {}) if isinstance(row.get("chunking_config_json"), dict) else {}
    strategy = raw_strategy if raw_strategy in SUPPORTED_CHUNKING_STRATEGIES else CHUNKING_STRATEGY_FIXED_LENGTH
    config = _normalize_fixed_length_chunking_config(
        {
            **default_chunking_payload()["config"],
            **raw_config,
        }
    )
    return {
        "strategy": strategy,
        "config": config,
    }


def build_chunking_state(row: dict[str, Any]) -> KnowledgeBaseChunking:
    payload = serialize_knowledge_base_chunking(row)
    config_payload = payload["config"]
    return KnowledgeBaseChunking(
        strategy=str(payload["strategy"]),
        config=FixedLengthChunkingConfig(
            unit=str(config_payload["unit"]),
            chunk_length=int(config_payload["chunk_length"]),
            chunk_overlap=int(config_payload["chunk_overlap"]),
        ),
    )


def chunk_text(
    text: str,
    *,
    chunking: KnowledgeBaseChunking,
    tokenizer: TextTokenizer,
) -> list[str]:
    normalized_text = text.strip()
    if not normalized_text:
        return []
    if chunking.strategy == CHUNKING_STRATEGY_FIXED_LENGTH:
        return _chunk_fixed_length_tokens(normalized_text, config=chunking.config, tokenizer=tokenizer)
    raise PlatformControlPlaneError(
        "invalid_chunking_strategy",
        "chunking.strategy is unsupported",
        status_code=400,
    )


def resolve_knowledge_base_tokenizer(
    database_url: str,
    *,
    knowledge_base: dict[str, Any],
) -> TextTokenizer:
    provider_instance_id = str(knowledge_base.get("embedding_provider_instance_id") or "").strip()
    if not provider_instance_id:
        raise PlatformControlPlaneError(
            "knowledge_base_embeddings_not_configured",
            "Knowledge base embeddings target is not configured.",
            status_code=409,
            details={"knowledge_base_id": knowledge_base.get("id")},
        )
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if provider_row is None:
        raise PlatformControlPlaneError(
            "embedding_provider_not_found",
            "Embeddings provider instance was not found",
            status_code=400,
        )
    provider_key = str(provider_row.get("provider_key") or "").strip().lower()
    if provider_key == "openai_compatible_cloud_embeddings":
        return _resolve_openai_compatible_cloud_tokenizer(knowledge_base)
    return _resolve_local_filesystem_tokenizer(provider_row=provider_row, knowledge_base=knowledge_base, database_url=database_url)


def _normalize_fixed_length_chunking_config(raw_config: Any) -> dict[str, Any]:
    if not isinstance(raw_config, dict):
        raise PlatformControlPlaneError(
            "invalid_chunking_config",
            "chunking.config must be an object",
            status_code=400,
        )
    unit = str(raw_config.get("unit") or "").strip().lower()
    if unit != CHUNKING_UNIT_TOKENS:
        raise PlatformControlPlaneError(
            "invalid_chunking_unit",
            "chunking.config.unit must be 'tokens'",
            status_code=400,
        )
    chunk_length = _coerce_positive_int(raw_config.get("chunk_length"), field_name="chunking.config.chunk_length")
    chunk_overlap = _coerce_nonnegative_int(raw_config.get("chunk_overlap"), field_name="chunking.config.chunk_overlap")
    if chunk_overlap >= chunk_length:
        raise PlatformControlPlaneError(
            "invalid_chunk_overlap",
            "chunking.config.chunk_overlap must be smaller than chunking.config.chunk_length",
            status_code=400,
        )
    return {
        "unit": unit,
        "chunk_length": chunk_length,
        "chunk_overlap": chunk_overlap,
    }


def _coerce_positive_int(value: Any, *, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError(
            "invalid_chunking_value",
            f"{field_name} must be a positive integer",
            status_code=400,
        ) from exc
    if normalized <= 0:
        raise PlatformControlPlaneError(
            "invalid_chunking_value",
            f"{field_name} must be a positive integer",
            status_code=400,
        )
    return normalized


def _coerce_nonnegative_int(value: Any, *, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError(
            "invalid_chunking_value",
            f"{field_name} must be a non-negative integer",
            status_code=400,
        ) from exc
    if normalized < 0:
        raise PlatformControlPlaneError(
            "invalid_chunking_value",
            f"{field_name} must be a non-negative integer",
            status_code=400,
        )
    return normalized


def _chunk_fixed_length_tokens(
    text: str,
    *,
    config: FixedLengthChunkingConfig,
    tokenizer: TextTokenizer,
) -> list[str]:
    token_ids = tokenizer.encode(text)
    if not token_ids:
        return []
    step = config.chunk_length - config.chunk_overlap
    chunks: list[str] = []
    for start in range(0, len(token_ids), step):
        window = token_ids[start : start + config.chunk_length]
        if not window:
            break
        decoded = tokenizer.decode(window).strip()
        if decoded:
            chunks.append(decoded)
        if start + config.chunk_length >= len(token_ids):
            break
    return chunks


def _resolve_openai_compatible_cloud_tokenizer(knowledge_base: dict[str, Any]) -> TextTokenizer:
    model_name = _cloud_tokenizer_model_name(knowledge_base)
    try:
        import tiktoken
    except ImportError as exc:
        raise PlatformControlPlaneError(
            "chunking_tokenizer_unavailable",
            "Token-based KB chunking requires the 'tiktoken' dependency for cloud embeddings providers.",
            status_code=500,
            details={"provider_key": "openai_compatible_cloud_embeddings"},
        ) from exc
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return _TiktokenTextTokenizer(encoding=encoding)


def _resolve_local_filesystem_tokenizer(
    *,
    provider_row: dict[str, Any],
    knowledge_base: dict[str, Any],
    database_url: str,
) -> TextTokenizer:
    local_path = resolve_local_tokenizer_path(provider_row=provider_row, knowledge_base=knowledge_base, database_url=database_url)
    if local_path is None:
        raise PlatformControlPlaneError(
            "chunking_tokenizer_unavailable",
            "Unable to resolve a local tokenizer path for the selected embeddings target.",
            status_code=409,
            details={
                "provider_instance_id": provider_row.get("id"),
                "knowledge_base_id": knowledge_base.get("id"),
            },
        )
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise PlatformControlPlaneError(
            "chunking_tokenizer_unavailable",
            "Token-based KB chunking requires the 'transformers' dependency for local embeddings providers.",
            status_code=500,
            details={"provider_key": provider_row.get("provider_key")},
        ) from exc
    try:
        tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
    except Exception as exc:  # pragma: no cover - exercised through service-level error tests
        raise PlatformControlPlaneError(
            "chunking_tokenizer_unavailable",
            "Unable to load the tokenizer for the selected local embeddings target.",
            status_code=409,
            details={
                "provider_instance_id": provider_row.get("id"),
                "knowledge_base_id": knowledge_base.get("id"),
                "local_path": local_path,
            },
        ) from exc
    return _TransformersTextTokenizer(tokenizer=tokenizer)


def _cloud_tokenizer_model_name(knowledge_base: dict[str, Any]) -> str:
    resource = embedding_resource_payload(knowledge_base)
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    provider_resource_id = str(resource.get("provider_resource_id") or "").strip()
    provider_model_id = str(metadata.get("provider_model_id") or "").strip()
    resource_id = str(resource.get("id") or "").strip()
    return provider_model_id or provider_resource_id or resource_id or "text-embedding-3-small"


def resolve_local_tokenizer_path(
    *,
    provider_row: dict[str, Any],
    knowledge_base: dict[str, Any],
    database_url: str,
) -> str | None:
    provider_config = dict(provider_row.get("config_json") or {})
    loaded_local_path = str(provider_config.get("loaded_local_path") or "").strip()
    if loaded_local_path:
        return loaded_local_path
    resource = embedding_resource_payload(knowledge_base)
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    metadata_local_path = str(metadata.get("local_path") or "").strip()
    if metadata_local_path:
        return metadata_local_path
    managed_model_id = str(metadata.get("managed_model_id") or "").strip() or str(resource.get("managed_model_id") or "").strip()
    if managed_model_id:
        model_row = modelops_repo.get_model(database_url, managed_model_id)
        if model_row is not None:
            model_local_path = str(model_row.get("local_path") or "").strip()
            if model_local_path:
                return model_local_path
    return None


def embedding_resource_payload(knowledge_base: dict[str, Any]) -> dict[str, Any]:
    vectorization_json = dict(knowledge_base.get("vectorization_json") or {})
    raw_resource = vectorization_json.get("embedding_resource")
    if isinstance(raw_resource, dict):
        return dict(raw_resource)
    embedding_resource_id = str(knowledge_base.get("embedding_resource_id") or "").strip()
    return {
        "id": embedding_resource_id,
        "provider_resource_id": embedding_resource_id,
        "metadata": {},
    }


def embedding_model_display_name(knowledge_base: dict[str, Any]) -> str:
    resource = embedding_resource_payload(knowledge_base)
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    return (
        str(resource.get("display_name") or "").strip()
        or str(metadata.get("name") or "").strip()
        or str(resource.get("provider_resource_id") or "").strip()
        or str(resource.get("id") or "").strip()
    )
