from __future__ import annotations

"""Backend KB retrieval execution pipeline; canonical contract: docs/services/retrieval_contract.md."""

import unicodedata
from typing import Any

from .context_management_retrieval_scoring import (
    calculate_hybrid_branch_top_k,
    coerce_query_result_score,
    fuse_hybrid_results,
    rank_branch_results,
)
from .context_management_retrieval_types import (
    KnowledgeBaseRetrievalBranchResult,
    KnowledgeBaseRetrievalExecution,
    KnowledgeBaseRetrievalOptions,
)
from .context_management_vectorization import (
    embed_knowledge_base_texts,
    validate_runtime_vectorization_compatibility,
)
from .platform_types import PlatformControlPlaneError


def preprocess_retrieval_query_text(query_text: str, *, query_preprocessing: str) -> str:
    if query_preprocessing != "normalize":
        return query_text
    decomposed = unicodedata.normalize("NFKD", query_text)
    without_diacritics = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = without_diacritics.lower()
    normalized_chars = [ch if ch.isalnum() or ch.isspace() else " " for ch in lowered]
    return " ".join("".join(normalized_chars).split())


def _coerce_branch_results(raw_results: Any) -> list[KnowledgeBaseRetrievalBranchResult]:
    if not isinstance(raw_results, list):
        return []
    branch_results: list[KnowledgeBaseRetrievalBranchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        branch_results.append(
            KnowledgeBaseRetrievalBranchResult(
                id=str(item.get("id") or "").strip(),
                text=str(item.get("text") or ""),
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                score=coerce_query_result_score(item.get("score")),
                score_kind=str(item.get("score_kind") or "").strip().lower(),
            )
        )
    return [result for result in branch_results if result.id]


def _run_vector_query(
    vector_adapter: Any,
    *,
    index_name: str,
    query_text: str | None,
    embedding: list[float] | None,
    top_k: int,
) -> tuple[str, list[KnowledgeBaseRetrievalBranchResult]]:
    query_payload = vector_adapter.query(
        index_name=index_name,
        query_text=query_text,
        embedding=embedding,
        top_k=top_k,
        filters={},
    )
    query_index = str(query_payload.get("index") or index_name).strip() or index_name
    return query_index, _coerce_branch_results(query_payload.get("results"))


def _run_semantic_branch(
    database_url: str,
    *,
    config: Any,
    knowledge_base: dict[str, Any],
    vector_adapter: Any,
    processed_query_text: str,
    top_k: int,
):
    from .platform_service import resolve_embeddings_adapter

    active_embeddings_adapter = resolve_embeddings_adapter(database_url, config)
    validate_runtime_vectorization_compatibility(
        knowledge_base,
        active_embeddings_binding=active_embeddings_adapter.binding,
    )
    embedding_payload = embed_knowledge_base_texts(
        database_url,
        config=config,
        knowledge_base=knowledge_base,
        texts=[processed_query_text],
    )
    query_embedding = embedding_payload["embeddings"][0]
    query_index, branch_results = _run_vector_query(
        vector_adapter,
        index_name=str(knowledge_base["index_name"]),
        query_text=None,
        embedding=query_embedding,
        top_k=top_k,
    )
    return query_index, rank_branch_results(branch_results, search_method="semantic")


def _run_keyword_branch(
    *,
    knowledge_base: dict[str, Any],
    vector_adapter: Any,
    processed_query_text: str,
    top_k: int,
):
    query_index, branch_results = _run_vector_query(
        vector_adapter,
        index_name=str(knowledge_base["index_name"]),
        query_text=processed_query_text,
        embedding=None,
        top_k=top_k,
    )
    return query_index, rank_branch_results(branch_results, search_method="keyword")


def run_knowledge_base_retrieval(
    database_url: str,
    *,
    config: Any,
    knowledge_base: dict[str, Any],
    vector_adapter: Any,
    options: KnowledgeBaseRetrievalOptions,
) -> KnowledgeBaseRetrievalExecution:
    processed_query_text = preprocess_retrieval_query_text(
        options.query_text,
        query_preprocessing=options.query_preprocessing,
    )
    if not processed_query_text:
        raise PlatformControlPlaneError(
            "invalid_query_text",
            "query_text must remain non-empty after preprocessing",
            status_code=400,
        )

    if options.search_method == "semantic":
        query_index, ranked_results = _run_semantic_branch(
            database_url,
            config=config,
            knowledge_base=knowledge_base,
            vector_adapter=vector_adapter,
            processed_query_text=processed_query_text,
            top_k=options.top_k,
        )
        return KnowledgeBaseRetrievalExecution(index=query_index, results=ranked_results)

    if options.search_method == "keyword":
        query_index, ranked_results = _run_keyword_branch(
            knowledge_base=knowledge_base,
            vector_adapter=vector_adapter,
            processed_query_text=processed_query_text,
            top_k=options.top_k,
        )
        return KnowledgeBaseRetrievalExecution(index=query_index, results=ranked_results)

    branch_top_k = calculate_hybrid_branch_top_k(options.top_k)
    semantic_index, semantic_results = _run_semantic_branch(
        database_url,
        config=config,
        knowledge_base=knowledge_base,
        vector_adapter=vector_adapter,
        processed_query_text=processed_query_text,
        top_k=branch_top_k,
    )
    keyword_index, keyword_results = _run_keyword_branch(
        knowledge_base=knowledge_base,
        vector_adapter=vector_adapter,
        processed_query_text=processed_query_text,
        top_k=branch_top_k,
    )
    return KnowledgeBaseRetrievalExecution(
        index=semantic_index or keyword_index or str(knowledge_base["index_name"]),
        results=fuse_hybrid_results(
            semantic_results,
            keyword_results,
            hybrid_alpha=options.hybrid_alpha if options.hybrid_alpha is not None else 0.5,
            top_k=options.top_k,
        ),
    )
