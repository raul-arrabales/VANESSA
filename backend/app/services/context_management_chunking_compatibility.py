from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ..repositories import platform_control_plane as platform_repo
from .context_management_chunking import (
    build_chunking_state,
    embedding_model_display_name,
    embedding_resource_payload,
    resolve_local_tokenizer_path,
)
from .platform_types import PlatformControlPlaneError


@dataclass(frozen=True)
class EmbeddingsChunkingConstraints:
    max_input_tokens: int
    special_tokens_per_input: int
    safe_chunk_length_max: int


def serialize_embeddings_chunking_constraints(
    constraints: EmbeddingsChunkingConstraints | None,
) -> dict[str, Any] | None:
    if constraints is None:
        return None
    return {
        "max_input_tokens": constraints.max_input_tokens,
        "special_tokens_per_input": constraints.special_tokens_per_input,
        "safe_chunk_length_max": constraints.safe_chunk_length_max,
    }


def resolve_knowledge_base_chunking_constraints(
    database_url: str,
    *,
    knowledge_base: dict[str, Any],
) -> EmbeddingsChunkingConstraints | None:
    provider_instance_id = str(knowledge_base.get("embedding_provider_instance_id") or "").strip()
    if not provider_instance_id:
        return None
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if not isinstance(provider_row, dict):
        return None
    return resolve_embedding_resource_chunking_constraints(
        database_url,
        provider_row=provider_row,
        resource=embedding_resource_payload(knowledge_base),
        knowledge_base=knowledge_base,
    )


def resolve_embedding_resource_chunking_constraints(
    database_url: str,
    *,
    provider_row: dict[str, Any],
    resource: dict[str, Any],
    knowledge_base: dict[str, Any] | None = None,
) -> EmbeddingsChunkingConstraints | None:
    provider_key = str(provider_row.get("provider_key") or "").strip().lower()
    if provider_key == "openai_compatible_cloud_embeddings":
        return None
    local_path = resolve_local_tokenizer_path(
        provider_row=provider_row,
        knowledge_base=knowledge_base or _knowledge_base_like_from_resource(provider_row, resource),
        database_url=database_url,
    )
    if not local_path:
        return None
    return _resolve_local_embeddings_chunking_constraints(local_path)


def assert_knowledge_base_chunking_compatible(
    database_url: str,
    *,
    knowledge_base: dict[str, Any],
    error_prefix: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> EmbeddingsChunkingConstraints | None:
    constraints = resolve_knowledge_base_chunking_constraints(database_url, knowledge_base=knowledge_base)
    if constraints is None:
        return None
    chunking = build_chunking_state(knowledge_base)
    chunk_length = int(chunking.config.chunk_length)
    if chunk_length <= constraints.safe_chunk_length_max:
        return constraints
    raise PlatformControlPlaneError(
        "knowledge_base_chunking_exceeds_embeddings_limit",
        (
            f"{error_prefix}: chunk length {chunk_length} exceeds the safe maximum "
            f"{constraints.safe_chunk_length_max} tokens for embeddings model "
            f"{embedding_model_display_name(knowledge_base)} "
            f"(model limit {constraints.max_input_tokens} including "
            f"{constraints.special_tokens_per_input} special tokens). "
            f"Update KB chunking to {constraints.safe_chunk_length_max} or smaller and retry."
        ),
        status_code=status_code,
        details={
            "knowledge_base_id": str(knowledge_base.get("id") or "").strip() or None,
            "embedding_resource_id": str(knowledge_base.get("embedding_resource_id") or "").strip() or None,
            "embedding_model_display_name": embedding_model_display_name(knowledge_base),
            "chunk_length": chunk_length,
            "chunk_overlap": int(chunking.config.chunk_overlap),
            "max_input_tokens": constraints.max_input_tokens,
            "special_tokens_per_input": constraints.special_tokens_per_input,
            "safe_chunk_length_max": constraints.safe_chunk_length_max,
            **(details or {}),
        },
    )


def _resolve_local_embeddings_chunking_constraints(local_path: str) -> EmbeddingsChunkingConstraints | None:
    model_root = Path(local_path).expanduser()
    max_input_tokens = _local_model_max_input_tokens(model_root)
    if max_input_tokens is None:
        return None
    special_tokens_per_input = _local_tokenizer_special_tokens_per_input(local_path)
    return EmbeddingsChunkingConstraints(
        max_input_tokens=max_input_tokens,
        special_tokens_per_input=special_tokens_per_input,
        safe_chunk_length_max=max(1, max_input_tokens - special_tokens_per_input),
    )


def _knowledge_base_like_from_resource(provider_row: dict[str, Any], resource: dict[str, Any]) -> dict[str, Any]:
    resource_id = str(resource.get("id") or resource.get("provider_resource_id") or "").strip()
    return {
        "embedding_provider_instance_id": str(provider_row.get("id") or "").strip(),
        "embedding_resource_id": resource_id,
        "vectorization_json": {
            "embedding_resource": dict(resource),
        },
    }


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _local_model_max_input_tokens(model_root: Path) -> int | None:
    sentence_bert_config = _read_json_file(model_root / "sentence_bert_config.json")
    token_limit = _normalized_finite_token_limit(sentence_bert_config.get("max_seq_length"))
    if token_limit is not None:
        return token_limit
    tokenizer_config = _read_json_file(model_root / "tokenizer_config.json")
    token_limit = _normalized_finite_token_limit(tokenizer_config.get("model_max_length"))
    if token_limit is not None:
        return token_limit
    config_payload = _read_json_file(model_root / "config.json")
    return _normalized_finite_token_limit(config_payload.get("max_position_embeddings"))


def _normalized_finite_token_limit(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    if normalized <= 0 or normalized >= 1_000_000:
        return None
    return normalized


def _local_tokenizer_special_tokens_per_input(local_path: str) -> int:
    try:
        from transformers import AutoTokenizer
    except ImportError:
        return 0
    try:
        tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
    except Exception:  # pragma: no cover - exercised via service-level fallback behavior
        return 0
    num_special_tokens_to_add = getattr(tokenizer, "num_special_tokens_to_add", None)
    if not callable(num_special_tokens_to_add):
        return 0
    try:
        special_tokens = int(num_special_tokens_to_add(pair=False))
    except Exception:  # pragma: no cover - defensive guard against tokenizer-specific implementations
        return 0
    return max(0, special_tokens)
