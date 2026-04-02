from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from app.services import context_management_chunking
from app.services import context_management_chunking_compatibility
from app.services.context_management_chunking import (
    CHUNKING_STRATEGY_FIXED_LENGTH,
    CHUNKING_UNIT_TOKENS,
    FixedLengthChunkingConfig,
    KnowledgeBaseChunking,
)
from app.services.platform_types import PlatformControlPlaneError


class _WhitespaceTokenizer:
    def __init__(self) -> None:
        self._vocabulary: dict[str, int] = {}
        self._reverse_vocabulary: dict[int, str] = {}

    def encode(self, text: str) -> list[int]:
        token_ids: list[int] = []
        for token in text.split():
            if token not in self._vocabulary:
                token_id = len(self._vocabulary) + 1
                self._vocabulary[token] = token_id
                self._reverse_vocabulary[token_id] = token
            token_ids.append(self._vocabulary[token])
        return token_ids

    def decode(self, token_ids: list[int]) -> str:
        return " ".join(self._reverse_vocabulary[token_id] for token_id in token_ids)


def _fixed_length_chunking(*, chunk_length: int, chunk_overlap: int) -> KnowledgeBaseChunking:
    return KnowledgeBaseChunking(
        strategy=CHUNKING_STRATEGY_FIXED_LENGTH,
        config=FixedLengthChunkingConfig(
            unit=CHUNKING_UNIT_TOKENS,
            chunk_length=chunk_length,
            chunk_overlap=chunk_overlap,
        ),
    )


def test_chunk_text_keeps_short_text_as_single_chunk():
    chunks = context_management_chunking.chunk_text(
        "alpha beta",
        chunking=_fixed_length_chunking(chunk_length=4, chunk_overlap=1),
        tokenizer=_WhitespaceTokenizer(),
    )

    assert chunks == ["alpha beta"]


def test_chunk_text_uses_strict_sliding_windows_with_overlap():
    chunks = context_management_chunking.chunk_text(
        "t0 t1 t2 t3 t4 t5",
        chunking=_fixed_length_chunking(chunk_length=3, chunk_overlap=1),
        tokenizer=_WhitespaceTokenizer(),
    )

    assert chunks == [
        "t0 t1 t2",
        "t2 t3 t4",
        "t4 t5",
    ]


class _RoundTripDriftTokenizer:
    def encode(self, text: str) -> list[int]:
        token_ids: list[int] = []
        for token in text.split():
            if token.startswith("t") and token[1:].isdigit():
                token_ids.append(int(token[1:]))
                continue
            if token == "expand-2":
                token_ids.extend([2, 200])
                continue
            raise AssertionError(f"Unexpected token: {token}")
        return token_ids

    def decode(self, token_ids: list[int]) -> str:
        parts: list[str] = []
        for token_id in token_ids:
            if token_id == 2:
                parts.append("expand-2")
            elif token_id == 200:
                parts.append("tail-2")
            else:
                parts.append(f"t{token_id}")
        return " ".join(parts)


def test_chunk_text_shrinks_decoded_windows_until_they_round_trip_within_limit():
    tokenizer = _RoundTripDriftTokenizer()

    chunks = context_management_chunking.chunk_text(
        "t0 t1 t2 t3 t4",
        chunking=_fixed_length_chunking(chunk_length=3, chunk_overlap=1),
        tokenizer=tokenizer,
    )

    assert chunks == [
        "t0 t1",
        "t1 expand-2",
        "expand-2 t3",
        "t3 t4",
    ]
    assert [len(tokenizer.encode(chunk)) for chunk in chunks] == [2, 3, 3, 2]


def test_chunk_text_strips_empty_input():
    chunks = context_management_chunking.chunk_text(
        "   ",
        chunking=_fixed_length_chunking(chunk_length=3, chunk_overlap=1),
        tokenizer=_WhitespaceTokenizer(),
    )

    assert chunks == []


def test_resolve_knowledge_base_tokenizer_uses_cloud_tiktoken_provider(monkeypatch: pytest.MonkeyPatch):
    class _FakeEncoding:
        def __init__(self) -> None:
            self.last_text = ""

        def encode(self, text: str) -> list[int]:
            self.last_text = text
            return [101, 102]

        def decode(self, token_ids: list[int]) -> str:
            return f"decoded:{','.join(str(token) for token in token_ids)}"

    encoding = _FakeEncoding()
    monkeypatch.setattr(
        context_management_chunking.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "embedding-provider-1",
            "provider_key": "openai_compatible_cloud_embeddings",
        },
    )
    monkeypatch.setitem(
        sys.modules,
        "tiktoken",
        SimpleNamespace(
            encoding_for_model=lambda model_name: encoding if model_name == "text-embedding-3-small" else None,
            get_encoding=lambda _name: encoding,
        ),
    )

    tokenizer = context_management_chunking.resolve_knowledge_base_tokenizer(
        "postgresql://ignored",
        knowledge_base={
            "id": "kb-primary",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_resource_id": "text-embedding-3-small",
            "vectorization_json": {
                "embedding_resource": {
                    "id": "text-embedding-3-small",
                    "provider_resource_id": "text-embedding-3-small",
                    "metadata": {},
                }
            },
        },
    )

    assert tokenizer.encode("hello world") == [101, 102]
    assert tokenizer.decode([1, 2]) == "decoded:1,2"


def test_resolve_knowledge_base_tokenizer_uses_local_transformers_provider(monkeypatch: pytest.MonkeyPatch):
    class _FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(local_path: str, *, local_files_only: bool):
            assert local_path == "/models/embeddings/local"
            assert local_files_only is True
            return SimpleNamespace(
                encode=lambda text, add_special_tokens=False: [len(text), 7] if add_special_tokens is False else [],
                decode=lambda token_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False: (
                    f"decoded:{','.join(str(token) for token in token_ids)}"
                    if skip_special_tokens is True and clean_up_tokenization_spaces is False
                    else ""
                ),
            )

    monkeypatch.setattr(
        context_management_chunking.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "embedding-provider-1",
            "provider_key": "vllm_embeddings_local",
            "config_json": {"loaded_local_path": "/models/embeddings/local"},
        },
    )
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=_FakeAutoTokenizer))

    tokenizer = context_management_chunking.resolve_knowledge_base_tokenizer(
        "postgresql://ignored",
        knowledge_base={
            "id": "kb-primary",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_resource_id": "local-embedding-model",
            "vectorization_json": {
                "embedding_resource": {
                    "id": "local-embedding-model",
                    "provider_resource_id": "local-embedding-model",
                    "metadata": {},
                }
            },
        },
    )

    assert tokenizer.encode("hello") == [5, 7]
    assert tokenizer.decode([1, 2]) == "decoded:1,2"


def test_resolve_knowledge_base_tokenizer_raises_when_local_path_cannot_be_resolved(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_chunking.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "embedding-provider-1",
            "provider_key": "vllm_embeddings_local",
            "config_json": {},
        },
    )
    monkeypatch.setattr(context_management_chunking.modelops_repo, "get_model", lambda *_args, **_kwargs: None)

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_chunking.resolve_knowledge_base_tokenizer(
            "postgresql://ignored",
            knowledge_base={
                "id": "kb-primary",
                "embedding_provider_instance_id": "embedding-provider-1",
                "embedding_resource_id": "local-embedding-model",
                "vectorization_json": {
                    "embedding_resource": {
                        "id": "local-embedding-model",
                        "provider_resource_id": "local-embedding-model",
                        "metadata": {},
                    }
                },
            },
        )

    assert exc_info.value.code == "chunking_tokenizer_unavailable"


def test_resolve_knowledge_base_chunking_constraints_uses_sentence_bert_max_length(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    model_path = tmp_path / "sentence-transformers-model"
    model_path.mkdir()
    (model_path / "sentence_bert_config.json").write_text(json.dumps({"max_seq_length": 256}), encoding="utf-8")
    (model_path / "tokenizer_config.json").write_text(json.dumps({"model_max_length": 512}), encoding="utf-8")
    (model_path / "config.json").write_text(json.dumps({"max_position_embeddings": 1024}), encoding="utf-8")

    class _FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(local_path: str, *, local_files_only: bool):
            assert local_path == str(model_path)
            assert local_files_only is True
            return SimpleNamespace(num_special_tokens_to_add=lambda pair=False: 2 if pair is False else 3)

    monkeypatch.setattr(
        context_management_chunking_compatibility.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "embedding-provider-1",
            "provider_key": "vllm_embeddings_local",
            "config_json": {"loaded_local_path": str(model_path)},
        },
    )
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=_FakeAutoTokenizer))

    constraints = context_management_chunking_compatibility.resolve_knowledge_base_chunking_constraints(
        "postgresql://ignored",
        knowledge_base={
            "id": "kb-primary",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_resource_id": "local-embedding-model",
            "vectorization_json": {
                "embedding_resource": {
                    "id": "local-embedding-model",
                    "provider_resource_id": "local-embedding-model",
                    "display_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "metadata": {},
                }
            },
        },
    )

    assert constraints is not None
    assert constraints.max_input_tokens == 256
    assert constraints.special_tokens_per_input == 2
    assert constraints.safe_chunk_length_max == 254
