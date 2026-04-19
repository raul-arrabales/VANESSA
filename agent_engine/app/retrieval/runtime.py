from __future__ import annotations

"""Agent-engine retrieval execution runtime; canonical contract: docs/services/retrieval_contract.md."""

from json import dumps
from typing import Any

from ..services.policy_runtime_gate import ExecutionBlockedError
from ..services.runtime_client import (
    EmbeddingsRuntimeClientError,
    VectorStoreRuntimeClientError,
    build_embeddings_runtime_client,
    build_vector_store_runtime_client,
)
from .options import normalize_retrieval_request
from .scoring import (
    calculate_hybrid_branch_top_k,
    coerce_query_result_score,
    fuse_hybrid_results,
    preprocess_retrieval_query_text,
    rank_branch_results,
)
from .types import (
    RankedRetrievalResult,
    RetrievalBranchResult,
    RetrievalCallMetadata,
    RetrievalRequest,
)

_REFERENCE_URI_KEYS = ("uri", "file_uri", "source_uri", "url", "source_url")
_REFERENCE_PATH_KEYS = ("source_path", "source_filename", "file_path", "filename")


def _retrieval_dependency_error(exc: EmbeddingsRuntimeClientError) -> ExecutionBlockedError:
    upstream = exc.details.get("upstream") if isinstance(exc.details.get("upstream"), dict) else {}
    error_payload = upstream.get("error") if isinstance(upstream.get("error"), dict) else {}
    detail_payload = upstream.get("detail") if isinstance(upstream.get("detail"), dict) else {}
    upstream_message = " ".join(
        [
            str(error_payload.get("message", "")).strip(),
            str(detail_payload.get("message", "")).strip(),
            str(upstream.get("message", "")).strip(),
        ]
    ).strip()
    normalized_message = upstream_message.lower()

    if "does not support embeddings" in normalized_message:
        return ExecutionBlockedError(
            code="EXEC_UPSTREAM_UNAVAILABLE",
            message=(
                "Knowledge retrieval is unavailable because the configured embeddings model "
                "does not support embeddings. Configure LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL "
                "to an embeddings-capable model and restart the stack."
            ),
            status_code=503,
            details=exc.details,
        )
    if exc.code == "embeddings_runtime_request_failed":
        return ExecutionBlockedError(
            code="EXEC_UPSTREAM_UNAVAILABLE",
            message="Knowledge retrieval is currently unavailable.",
            status_code=503,
            details=exc.details,
        )
    return ExecutionBlockedError(
        code="EXEC_INTERNAL_ERROR",
        message="Execution failed internally",
        status_code=500,
        details=exc.details,
    )


def coerce_execution_messages(execution_input: dict[str, Any]) -> list[dict[str, Any]]:
    raw_messages = execution_input.get("messages")
    if isinstance(raw_messages, list):
        normalized = _coerce_messages(raw_messages)
        if normalized:
            return normalized

    prompt = str(execution_input.get("prompt", "")).strip()
    if prompt:
        return [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    return []


def _coerce_messages(messages: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        content = item.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text:
                normalized.append({"role": role, "content": [{"type": "text", "text": text}]})
            continue
        if not isinstance(content, list):
            continue
        parts: list[dict[str, str]] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if str(part.get("type", "")).strip().lower() != "text":
                continue
            text = str(part.get("text", "")).strip()
            if text:
                parts.append({"type": "text", "text": text})
        if parts:
            normalized.append({"role": role, "content": parts})
    return normalized


def _raise_vector_blocked_error(exc: VectorStoreRuntimeClientError) -> None:
    if exc.code == "vector_runtime_timeout":
        raise ExecutionBlockedError(
            code="EXEC_TIMEOUT",
            message="Execution timed out",
            status_code=504,
            details=exc.details,
        ) from exc
    if exc.code in {"vector_runtime_unreachable", "vector_runtime_upstream_unavailable"}:
        raise ExecutionBlockedError(
            code="EXEC_UPSTREAM_UNAVAILABLE",
            message="Upstream LLM/tool dependency unavailable",
            status_code=503,
            details=exc.details,
        ) from exc
    raise ExecutionBlockedError(
        code="EXEC_INTERNAL_ERROR",
        message="Execution failed internally",
        status_code=500,
        details=exc.details,
    ) from exc


def _build_embedding_call(runtime_snapshot: dict[str, Any], embedding_payload: dict[str, Any]) -> dict[str, Any]:
    embeddings_binding = runtime_snapshot.get("capabilities", {}).get("embeddings", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    return {
        "provider_slug": embeddings_binding.get("slug"),
        "provider_key": embeddings_binding.get("provider_key"),
        "deployment_profile_slug": deployment_profile.get("slug"),
        "requested_model": embedding_payload.get("requested_model"),
        "input_count": 1,
        "dimension": int(embedding_payload.get("dimension", 0) or 0),
        "status_code": int(embedding_payload.get("status_code", 200) or 200),
    }


def _coerce_branch_results(raw_results: Any) -> list[RetrievalBranchResult]:
    if not isinstance(raw_results, list):
        return []
    branch_results: list[RetrievalBranchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        result_id = str(item.get("id") or "").strip()
        if not result_id:
            continue
        branch_results.append(
            RetrievalBranchResult(
                id=result_id,
                text=str(item.get("text") or ""),
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                score=coerce_query_result_score(item.get("score")),
                score_kind=str(item.get("score_kind") or "").strip().lower(),
            )
        )
    return branch_results


def _run_vector_query(
    client: Any,
    *,
    retrieval_request: RetrievalRequest,
    query_text: str,
    search_method: str,
    embedding: list[float] | None,
    top_k: int,
) -> tuple[str, list[RetrievalBranchResult]]:
    query_payload = client.query(
        index_name=retrieval_request.index,
        search_method=search_method,
        embedding=embedding,
        top_k=top_k,
        filters=dict(retrieval_request.filters),
        query_text=query_text,
    )
    query_index = str(query_payload.get("index") or retrieval_request.index).strip() or retrieval_request.index
    return query_index, _coerce_branch_results(query_payload.get("results"))


def _semantic_retrieval(
    *,
    runtime_snapshot: dict[str, Any],
    retrieval_request: RetrievalRequest,
    processed_query_text: str,
    top_k: int,
) -> tuple[dict[str, Any], str, list[RankedRetrievalResult]]:
    embeddings_client = build_embeddings_runtime_client(runtime_snapshot)
    embedding_payload = embeddings_client.embed_texts(texts=[processed_query_text])
    vector_client = build_vector_store_runtime_client(runtime_snapshot)
    query_index, branch_results = _run_vector_query(
        vector_client,
        retrieval_request=retrieval_request,
        query_text=processed_query_text,
        search_method="semantic",
        embedding=list(embedding_payload["embeddings"][0]),
        top_k=top_k,
    )
    return _build_embedding_call(runtime_snapshot, embedding_payload), query_index, rank_branch_results(
        branch_results,
        search_method="semantic",
    )


def _keyword_retrieval(
    *,
    runtime_snapshot: dict[str, Any],
    retrieval_request: RetrievalRequest,
    processed_query_text: str,
    top_k: int,
) -> tuple[str, list[RankedRetrievalResult]]:
    vector_client = build_vector_store_runtime_client(runtime_snapshot)
    query_index, branch_results = _run_vector_query(
        vector_client,
        retrieval_request=retrieval_request,
        query_text=processed_query_text,
        search_method="keyword",
        embedding=None,
        top_k=top_k,
    )
    return query_index, rank_branch_results(branch_results, search_method="keyword")


def _serialize_ranked_result(result: RankedRetrievalResult) -> dict[str, Any]:
    payload = {
        "id": result.id,
        "text": result.text,
        "metadata": result.metadata,
        "score": result.score,
        "score_kind": result.score_kind,
        "relevance_score": result.relevance_score,
        "relevance_kind": result.relevance_kind,
    }
    if result.relevance_components is not None:
        components = {
            key: value
            for key, value in {
                "semantic_score": result.relevance_components.semantic_score,
                "keyword_score": result.relevance_components.keyword_score,
            }.items()
            if isinstance(value, (int, float))
        }
        if components:
            payload["relevance_components"] = components
    return payload


def _serialize_retrieval_call(
    runtime_snapshot: dict[str, Any],
    *,
    metadata: RetrievalCallMetadata,
    results: list[RankedRetrievalResult],
) -> dict[str, Any]:
    vector_binding = runtime_snapshot.get("capabilities", {}).get("vector_store", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    payload = {
        "provider_slug": vector_binding.get("slug"),
        "provider_key": vector_binding.get("provider_key"),
        "deployment_profile_slug": deployment_profile.get("slug"),
        "index": metadata.index,
        "query": metadata.query,
        "top_k": metadata.top_k,
        "search_method": metadata.search_method,
        "query_preprocessing": metadata.query_preprocessing,
        "result_count": metadata.result_count,
        "results": [_serialize_ranked_result(item) for item in results],
    }
    if metadata.hybrid_alpha is not None:
        payload["hybrid_alpha"] = metadata.hybrid_alpha
    return payload


def execute_retrieval_call(
    *,
    retrieval_request: RetrievalRequest | None,
    platform_runtime: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    if retrieval_request is None:
        return None, None, []

    runtime_snapshot = platform_runtime if isinstance(platform_runtime, dict) else {}
    processed_query_text = preprocess_retrieval_query_text(
        retrieval_request.query,
        query_preprocessing=retrieval_request.query_preprocessing,
    )
    if not processed_query_text:
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
            details={"reason": "retrieval_query_empty_after_preprocessing"},
        )

    embedding_call: dict[str, Any] | None = None
    try:
        if retrieval_request.search_method == "semantic":
            embedding_call, query_index, ranked_results = _semantic_retrieval(
                runtime_snapshot=runtime_snapshot,
                retrieval_request=retrieval_request,
                processed_query_text=processed_query_text,
                top_k=retrieval_request.top_k,
            )
        elif retrieval_request.search_method == "keyword":
            query_index, ranked_results = _keyword_retrieval(
                runtime_snapshot=runtime_snapshot,
                retrieval_request=retrieval_request,
                processed_query_text=processed_query_text,
                top_k=retrieval_request.top_k,
            )
        else:
            branch_top_k = calculate_hybrid_branch_top_k(retrieval_request.top_k)
            embedding_call, semantic_index, semantic_results = _semantic_retrieval(
                runtime_snapshot=runtime_snapshot,
                retrieval_request=retrieval_request,
                processed_query_text=processed_query_text,
                top_k=branch_top_k,
            )
            keyword_index, keyword_results = _keyword_retrieval(
                runtime_snapshot=runtime_snapshot,
                retrieval_request=retrieval_request,
                processed_query_text=processed_query_text,
                top_k=branch_top_k,
            )
            query_index = semantic_index or keyword_index or retrieval_request.index
            ranked_results = fuse_hybrid_results(
                semantic_results,
                keyword_results,
                hybrid_alpha=retrieval_request.hybrid_alpha if retrieval_request.hybrid_alpha is not None else 0.5,
                top_k=retrieval_request.top_k,
            )
    except EmbeddingsRuntimeClientError as exc:
        if exc.code == "embeddings_runtime_timeout":
            raise ExecutionBlockedError(
                code="EXEC_TIMEOUT",
                message="Execution timed out",
                status_code=504,
                details=exc.details,
            ) from exc
        if exc.code in {"embeddings_runtime_unreachable", "embeddings_runtime_upstream_unavailable"}:
            raise ExecutionBlockedError(
                code="EXEC_UPSTREAM_UNAVAILABLE",
                message="Upstream LLM/tool dependency unavailable",
                status_code=503,
                details=exc.details,
            ) from exc
        raise _retrieval_dependency_error(exc) from exc
    except VectorStoreRuntimeClientError as exc:
        _raise_vector_blocked_error(exc)

    retrieval_call = _serialize_retrieval_call(
        runtime_snapshot,
        metadata=RetrievalCallMetadata(
            index=query_index,
            query=processed_query_text,
            top_k=retrieval_request.top_k,
            search_method=retrieval_request.search_method,
            query_preprocessing=retrieval_request.query_preprocessing,
            hybrid_alpha=retrieval_request.hybrid_alpha if retrieval_request.search_method == "hybrid" else None,
            result_count=len(ranked_results),
        ),
        results=ranked_results,
    )
    return embedding_call, retrieval_call, retrieval_call["results"]


def prepend_retrieval_context(
    messages: list[dict[str, Any]],
    *,
    retrieval_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not retrieval_results:
        return messages

    context_lines = [
        "Use the following retrieved context if it is relevant to the user's request.",
        (
            "When you use retrieved context, cite the supporting reference inline with "
            "bracketed numeric citations such as [1] or [1, 2]."
        ),
        "Do not cite a reference unless it supports the sentence that uses the citation.",
    ]
    grouped_results = _group_retrieval_results_for_citations(retrieval_results)
    for index, group in enumerate(grouped_results, start=1):
        context_lines.append(
            f"Reference [{index}] title={group['title']} file={group['file_reference']}"
        )
        for result in group["results"]:
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            metadata_json = dumps(metadata, sort_keys=True, separators=(",", ":"))
            context_lines.append(
                f"Chunk id={result.get('id', '')} metadata={metadata_json}\n{str(result.get('text', '')).strip()}"
            )
    return [
        {"role": "system", "content": [{"type": "text", "text": "\n\n".join(context_lines)}]},
        *messages,
    ]


def _group_retrieval_results_for_citations(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for result in results:
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        group_key = _reference_group_key(result, metadata)
        if group_key not in groups:
            order.append(group_key)
            groups[group_key] = {
                "title": _reference_title(result, metadata),
                "file_reference": _reference_file_value(metadata, result),
                "results": [],
            }
        groups[group_key]["results"].append(result)
    return [groups[group_key] for group_key in order]


def _reference_group_key(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    for value in (
        _first_metadata_string(metadata, _REFERENCE_URI_KEYS),
        _first_metadata_string(metadata, _REFERENCE_PATH_KEYS),
        _string_or_none(metadata.get("document_id")),
        _string_or_none(metadata.get("title")),
        _string_or_none(result.get("id")),
    ):
        if value:
            return value
    return "unknown-source"


def _reference_title(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        _string_or_none(metadata.get("title"))
        or _string_or_none(metadata.get("source_display_name"))
        or _string_or_none(metadata.get("source_name"))
        or _string_or_none(metadata.get("source_filename"))
        or _string_or_none(metadata.get("source_path"))
        or _string_or_none(result.get("id"))
        or "Source"
    )


def _reference_file_value(metadata: dict[str, Any], result: dict[str, Any]) -> str:
    return (
        _first_metadata_string(metadata, _REFERENCE_URI_KEYS)
        or _first_metadata_string(metadata, _REFERENCE_PATH_KEYS)
        or _string_or_none(metadata.get("document_id"))
        or _string_or_none(result.get("id"))
        or "Source"
    )


def _first_metadata_string(metadata: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        normalized = _string_or_none(metadata.get(key))
        if normalized:
            return normalized
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
