from __future__ import annotations

from datetime import datetime, timezone
from json import dumps
from typing import Any
from uuid import uuid4

from ..repositories import executions as executions_repo
from ..schemas.agent_executions import AgentExecutionRecord
from .policy_runtime_gate import (
    ExecutionBlockedError,
    require_agent_execute_permission,
    resolve_agent_spec,
    resolve_runtime_profile,
    validate_runtime_and_dependencies,
)
from .runtime_client import (
    EmbeddingsRuntimeClientError,
    LlmRuntimeClientError,
    VectorStoreRuntimeClientError,
    build_embeddings_runtime_client,
    build_llm_runtime_client,
    build_vector_store_runtime_client,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def _raise_simulated_error_if_requested(execution_input: dict[str, Any]) -> None:
    simulate_error = str(execution_input.get("simulate_error", "")).strip().lower()
    if simulate_error == "timeout":
        raise ExecutionBlockedError(code="EXEC_TIMEOUT", message="Execution timed out", status_code=504)
    if simulate_error == "upstream_unavailable":
        raise ExecutionBlockedError(
            code="EXEC_UPSTREAM_UNAVAILABLE",
            message="Upstream LLM/tool dependency unavailable",
            status_code=503,
        )
    if simulate_error == "internal":
        raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500)


def _deterministic_execution_result(*, agent_id: str, runtime_profile: str) -> dict[str, Any]:
    output_text = f"Agent '{agent_id}' executed in {runtime_profile} profile"
    return {
        "output_text": output_text,
        "tool_calls": [],
        "embedding_calls": [],
        "model_calls": [],
        "retrieval_calls": [],
    }


def _coerce_execution_messages(execution_input: dict[str, Any]) -> list[dict[str, Any]]:
    raw_messages = execution_input.get("messages")
    if isinstance(raw_messages, list):
        normalized = _coerce_messages(raw_messages)
        if normalized:
            return normalized

    prompt = str(execution_input.get("prompt", "")).strip()
    if prompt:
        return [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    return []


def _normalize_retrieval_request(execution_input: dict[str, Any]) -> dict[str, Any] | None:
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

    return {
        "index": index_name,
        "query": query_text,
        "top_k": normalized_top_k,
        "filters": normalized_filters,
    }


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


def _execute_retrieval_call(
    *,
    retrieval_request: dict[str, Any] | None,
    platform_runtime: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    if retrieval_request is None:
        return None, None, []

    runtime_snapshot = platform_runtime if isinstance(platform_runtime, dict) else {}
    try:
        embeddings_client = build_embeddings_runtime_client(runtime_snapshot)
        embedding_payload = embeddings_client.embed_texts(texts=[str(retrieval_request["query"])])
        client = build_vector_store_runtime_client(runtime_snapshot)
        query_payload = client.query(
            index_name=str(retrieval_request["index"]),
            embedding=list(embedding_payload["embeddings"][0]),
            top_k=int(retrieval_request["top_k"]),
            filters=dict(retrieval_request["filters"]),
            query_text=str(retrieval_request["query"]),
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
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
            details=exc.details,
        ) from exc
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
        "index": retrieval_request["index"],
        "query": retrieval_request["query"],
        "top_k": retrieval_request["top_k"],
        "result_count": len(results),
        "results": results,
    }
    return embedding_call, retrieval_call, results


def _prepend_retrieval_context(
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
        {
            "role": "system",
            "content": [{"type": "text", "text": "\n\n".join(context_lines)}],
        },
        *messages,
    ]


def _execute_model_call(
    *,
    execution_input: dict[str, Any],
    agent_id: str,
    runtime_profile: str,
    model_ref: str | None,
    platform_runtime: dict[str, Any] | None,
    retrieval_request: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    _raise_simulated_error_if_requested(execution_input)
    messages = _coerce_execution_messages(execution_input)
    if not messages and retrieval_request is None:
        return _deterministic_execution_result(agent_id=agent_id, runtime_profile=runtime_profile), model_ref

    embedding_call, retrieval_call, retrieval_results = _execute_retrieval_call(
        retrieval_request=retrieval_request,
        platform_runtime=platform_runtime if isinstance(platform_runtime, dict) else None,
    )
    effective_messages = _prepend_retrieval_context(messages, retrieval_results=retrieval_results)

    runtime_snapshot = platform_runtime if isinstance(platform_runtime, dict) else {}
    try:
        client = build_llm_runtime_client(runtime_snapshot)
        completion = client.chat_completion(
            requested_model=model_ref,
            messages=effective_messages,
        )
    except LlmRuntimeClientError as exc:
        if exc.code == "runtime_timeout":
            raise ExecutionBlockedError(
                code="EXEC_TIMEOUT",
                message="Execution timed out",
                status_code=504,
                details=exc.details,
            ) from exc
        if exc.code in {"runtime_unreachable", "runtime_upstream_unavailable"}:
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

    llm_binding = runtime_snapshot.get("capabilities", {}).get("llm_inference", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    effective_model = str(completion.get("requested_model", "")).strip() or model_ref
    return (
        {
            "output_text": str(completion.get("output_text", "")),
            "tool_calls": [],
            "embedding_calls": [embedding_call] if embedding_call is not None else [],
            "model_calls": [
                {
                    "provider_slug": llm_binding.get("slug"),
                    "provider_key": llm_binding.get("provider_key"),
                    "deployment_profile_slug": deployment_profile.get("slug"),
                    "requested_model": effective_model,
                    "status_code": int(completion.get("status_code", 200) or 200),
                }
            ],
            "retrieval_calls": [retrieval_call] if retrieval_call is not None else [],
        },
        effective_model,
    )


def _build_execution(
    *,
    execution_id: str,
    status: str,
    agent_ref: str,
    agent_version: str,
    model_ref: str | None,
    runtime_profile: str,
    created_at: str,
    started_at: str | None,
    finished_at: str | None,
    result: dict[str, Any] | None,
    error: dict[str, Any] | None,
) -> AgentExecutionRecord:
    return AgentExecutionRecord(
        id=execution_id,
        status=status,
        agent_ref=agent_ref,
        agent_version=agent_version,
        model_ref=model_ref,
        runtime_profile=runtime_profile,
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        result=result,
        error=error,
    )


def create_execution(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    agent_id = str(payload.get("agent_id", "")).strip()
    if not agent_id:
        raise ValueError("invalid_agent_id")

    execution_input = payload.get("input")
    if execution_input is not None and not isinstance(execution_input, dict):
        raise ValueError("invalid_input")
    normalized_input = execution_input if isinstance(execution_input, dict) else {}
    normalized_retrieval = _normalize_retrieval_request(normalized_input)
    normalized_messages = _coerce_execution_messages(normalized_input)
    if normalized_retrieval is not None and not normalized_messages:
        raise ValueError("invalid_retrieval_input")
    platform_runtime = payload.get("platform_runtime")

    requested_by_user_id = int(payload.get("requested_by_user_id", 0) or 0)
    requested_by_role = str(payload.get("requested_by_role", "user")).strip().lower() or "user"
    runtime_profile = resolve_runtime_profile(payload.get("runtime_profile"))

    execution_id = str(uuid4())
    created_at = _iso_now()
    queued = _build_execution(
        execution_id=execution_id,
        status="queued",
        agent_ref=agent_id,
        agent_version="v1",
        model_ref=None,
        runtime_profile=runtime_profile,
        created_at=created_at,
        started_at=None,
        finished_at=None,
        result=None,
        error=None,
    )
    executions_repo.save_execution(
        queued,
        requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
        input_payload=normalized_input,
    )

    try:
        agent_entity = resolve_agent_spec(agent_id=agent_id)
        require_agent_execute_permission(
            user_id=requested_by_user_id,
            user_role=requested_by_role,
            agent_id=agent_id,
        )
        agent_version, model_ref = validate_runtime_and_dependencies(
            agent_entity=agent_entity,
            runtime_profile=runtime_profile,
        )
        running_started_at = _iso_now()
        running = _build_execution(
            execution_id=execution_id,
            status="running",
            agent_ref=agent_id,
            agent_version=agent_version,
            model_ref=model_ref,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=running_started_at,
            finished_at=None,
            result=None,
            error=None,
        )
        executions_repo.save_execution(
            running,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        result, effective_model_ref = _execute_model_call(
            execution_input=normalized_input,
            agent_id=agent_id,
            runtime_profile=runtime_profile,
            model_ref=model_ref,
            platform_runtime=platform_runtime if isinstance(platform_runtime, dict) else None,
            retrieval_request=normalized_retrieval,
        )
        finished = _build_execution(
            execution_id=execution_id,
            status="succeeded",
            agent_ref=agent_id,
            agent_version=agent_version,
            model_ref=effective_model_ref,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=running_started_at,
            finished_at=_iso_now(),
            result=result,
            error=None,
        )
        executions_repo.save_execution(
            finished,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        return {"execution": finished.to_payload()}, 201
    except ExecutionBlockedError as exc:
        blocked_status = "blocked" if exc.status_code in {403} else "failed"
        failed_execution = _build_execution(
            execution_id=execution_id,
            status=blocked_status,
            agent_ref=agent_id,
            agent_version="v1",
            model_ref=None,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=None,
            finished_at=_iso_now(),
            result=None,
            error=_error_payload(exc.code, exc.message, exc.details),
        )
        executions_repo.save_execution(
            failed_execution,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        raise
    except Exception as exc:
        failed_execution = _build_execution(
            execution_id=execution_id,
            status="failed",
            agent_ref=agent_id,
            agent_version="v1",
            model_ref=None,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=None,
            finished_at=_iso_now(),
            result=None,
            error=_error_payload("EXEC_INTERNAL_ERROR", str(exc)),
        )
        executions_repo.save_execution(
            failed_execution,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
        ) from exc


def get_execution(execution_id: str) -> tuple[dict[str, Any], int]:
    normalized_id = execution_id.strip()
    if not normalized_id:
        raise ValueError("invalid_execution_id")
    execution = executions_repo.get_execution(normalized_id)
    if execution is None:
        raise ExecutionBlockedError(
            code="execution_not_found",
            message="Execution not found",
            status_code=404,
        )
    return {"execution": execution.to_payload()}, 200
