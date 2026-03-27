from __future__ import annotations

from json import dumps
from typing import Any

from ..execution_pipeline.types import RetrievalRequest
from ..services.policy_runtime_gate import ExecutionBlockedError
from ..services.runtime_client import (
    EmbeddingsRuntimeClientError,
    VectorStoreRuntimeClientError,
    build_embeddings_runtime_client,
    build_vector_store_runtime_client,
)


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


def normalize_retrieval_request(execution_input: dict[str, Any]) -> RetrievalRequest | None:
    retrieval = execution_input.get("retrieval")
    if retrieval is None:
        return None
    if not isinstance(retrieval, dict):
        raise ValueError("invalid_retrieval_input")

    index_name = str(retrieval.get("index", "")).strip()
    if not index_name:
        raise ValueError("invalid_retrieval_input")

    raw_query = retrieval.get("query")
    if raw_query is not None:
        query_text = str(raw_query).strip()
        if not query_text:
            raise ValueError("invalid_retrieval_input")
    else:
        query_text = _derive_retrieval_query(execution_input)
        if not query_text:
            raise ValueError("invalid_retrieval_input")

    top_k = retrieval.get("top_k", 5)
    if isinstance(top_k, bool):
        raise ValueError("invalid_retrieval_input")
    try:
        normalized_top_k = int(top_k)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_retrieval_input") from exc
    if normalized_top_k <= 0:
        raise ValueError("invalid_retrieval_input")

    filters = retrieval.get("filters", {})
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        raise ValueError("invalid_retrieval_input")

    normalized_filters: dict[str, Any] = {}
    for key, value in filters.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            raise ValueError("invalid_retrieval_input")
        if isinstance(value, bool):
            normalized_filters[normalized_key] = value
            continue
        if isinstance(value, (int, float, str)):
            normalized_filters[normalized_key] = value
            continue
        raise ValueError("invalid_retrieval_input")

    return RetrievalRequest(
        index=index_name,
        query=query_text,
        top_k=normalized_top_k,
        filters=normalized_filters,
    )


def _derive_retrieval_query(execution_input: dict[str, Any]) -> str:
    prompt = str(execution_input.get("prompt", "")).strip()
    if prompt:
        return prompt

    raw_messages = execution_input.get("messages")
    if not isinstance(raw_messages, list):
        return ""
    for item in reversed(raw_messages):
        if not isinstance(item, dict):
            continue
        if str(item.get("role", "")).strip().lower() != "user":
            continue
        text = _message_text(item.get("content"))
        if text:
            return text
    return ""


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


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if str(part.get("type", "")).strip().lower() != "text":
            continue
        text = str(part.get("text", "")).strip()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def execute_retrieval_call(
    *,
    retrieval_request: RetrievalRequest | None,
    platform_runtime: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    if retrieval_request is None:
        return None, None, []

    runtime_snapshot = platform_runtime if isinstance(platform_runtime, dict) else {}
    try:
        embeddings_client = build_embeddings_runtime_client(runtime_snapshot)
        embedding_payload = embeddings_client.embed_texts(texts=[retrieval_request.query])
        client = build_vector_store_runtime_client(runtime_snapshot)
        query_payload = client.query(
            index_name=retrieval_request.index,
            embedding=list(embedding_payload["embeddings"][0]),
            top_k=retrieval_request.top_k,
            filters=dict(retrieval_request.filters),
            query_text=retrieval_request.query,
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

    embeddings_binding = runtime_snapshot.get("capabilities", {}).get("embeddings", {})
    vector_binding = runtime_snapshot.get("capabilities", {}).get("vector_store", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    results = query_payload.get("results") if isinstance(query_payload.get("results"), list) else []
    embedding_call = {
        "provider_slug": embeddings_binding.get("slug"),
        "provider_key": embeddings_binding.get("provider_key"),
        "deployment_profile_slug": deployment_profile.get("slug"),
        "requested_model": embedding_payload.get("requested_model"),
        "input_count": 1,
        "dimension": int(embedding_payload.get("dimension", 0) or 0),
        "status_code": int(embedding_payload.get("status_code", 200) or 200),
    }
    retrieval_call = {
        "provider_slug": vector_binding.get("slug"),
        "provider_key": vector_binding.get("provider_key"),
        "deployment_profile_slug": deployment_profile.get("slug"),
        "index": retrieval_request.index,
        "query": retrieval_request.query,
        "top_k": retrieval_request.top_k,
        "result_count": len(results),
        "results": results,
    }
    return embedding_call, retrieval_call, results


def prepend_retrieval_context(
    messages: list[dict[str, Any]],
    *,
    retrieval_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not retrieval_results:
        return messages

    context_lines = ["Use the following retrieved context if it is relevant to the user's request."]
    for index, result in enumerate(retrieval_results, start=1):
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        metadata_json = dumps(metadata, sort_keys=True, separators=(",", ":"))
        context_lines.append(
            f"{index}. id={result.get('id', '')} metadata={metadata_json}\n{str(result.get('text', '')).strip()}"
        )
    return [
        {"role": "system", "content": [{"type": "text", "text": "\n\n".join(context_lines)}]},
        *messages,
    ]
