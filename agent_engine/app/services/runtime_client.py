from __future__ import annotations

from abc import ABC, abstractmethod
from json import dumps, loads
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_DEFAULT_HTTP_TIMEOUT_SECONDS = 5.0


class LlmRuntimeClientError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class VectorStoreRuntimeClientError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class EmbeddingsRuntimeClientError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class LlmRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], llm_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.llm_binding = llm_binding

    @abstractmethod
    def chat_completion(
        self,
        *,
        requested_model: str | None,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raise NotImplementedError


class VectorStoreRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], vector_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.vector_binding = vector_binding

    @abstractmethod
    def query(
        self,
        *,
        index_name: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
        query_text: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class EmbeddingsRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], embeddings_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.embeddings_binding = embeddings_binding

    @abstractmethod
    def embed_texts(
        self,
        *,
        texts: list[str],
    ) -> dict[str, Any]:
        raise NotImplementedError


class OpenAICompatibleLlmRuntimeClient(LlmRuntimeClient):
    def chat_completion(
        self,
        *,
        requested_model: str | None,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        effective_model = _resolve_effective_model(requested_model, self.llm_binding)
        payload = _build_request_payload(self.llm_binding, effective_model, messages)
        response_payload, status_code = http_json_request(
            self._chat_url(),
            method="POST",
            payload=payload,
        )
        if response_payload is None:
            raise LlmRuntimeClientError(
                code="runtime_unreachable",
                message="LLM runtime unavailable",
                status_code=status_code,
                details={"provider_slug": self.llm_binding.get("slug"), "status_code": status_code},
            )
        if not 200 <= status_code < 300:
            error_code = (
                "runtime_timeout"
                if status_code == 504
                else "runtime_upstream_unavailable"
                if status_code >= 502
                else "runtime_request_failed"
            )
            raise LlmRuntimeClientError(
                code=error_code,
                message="LLM runtime request failed",
                status_code=status_code,
                details={
                    "provider_slug": self.llm_binding.get("slug"),
                    "status_code": status_code,
                    "upstream": response_payload,
                },
            )

        return {
            "output_text": _extract_output_text(response_payload),
            "status_code": status_code,
            "requested_model": effective_model,
        }

    def _chat_url(self) -> str:
        config = self.llm_binding.get("config") if isinstance(self.llm_binding.get("config"), dict) else {}
        chat_path = str(config.get("chat_completion_path", "/v1/chat/completions")).strip() or "/v1/chat/completions"
        endpoint_url = str(self.llm_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + chat_path


class WeaviateVectorStoreRuntimeClient(VectorStoreRuntimeClient):
    def query(
        self,
        *,
        index_name: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
        query_text: str | None = None,
    ) -> dict[str, Any]:
        class_name = _coerce_weaviate_class_name(index_name)
        operation = _build_weaviate_query_operation(
            class_name=class_name,
            embedding=embedding,
            top_k=top_k,
            filters=filters,
        )
        payload, status_code = http_json_request(
            self._graphql_url(),
            method="POST",
            payload={"query": operation["query"]},
        )
        if payload is None:
            error_code = "vector_runtime_timeout" if status_code == 504 else "vector_runtime_unreachable"
            raise VectorStoreRuntimeClientError(
                code=error_code,
                message="Vector runtime unavailable",
                status_code=status_code,
                details={"provider_slug": self.vector_binding.get("slug"), "status_code": status_code},
            )
        if not 200 <= status_code < 300:
            error_code = (
                "vector_runtime_timeout"
                if status_code == 504
                else "vector_runtime_upstream_unavailable"
                if status_code >= 502
                else "vector_runtime_request_failed"
            )
            raise VectorStoreRuntimeClientError(
                code=error_code,
                message="Vector runtime request failed",
                status_code=status_code,
                details={
                    "provider_slug": self.vector_binding.get("slug"),
                    "status_code": status_code,
                    "upstream": payload,
                },
            )
        if isinstance(payload.get("errors"), list) and payload["errors"]:
            raise VectorStoreRuntimeClientError(
                code="vector_runtime_request_failed",
                message="Vector runtime query failed",
                status_code=502,
                details={
                    "provider_slug": self.vector_binding.get("slug"),
                    "status_code": 502,
                    "upstream": payload,
                },
            )

        rows = (((payload.get("data") or {}).get("Get") or {}).get(class_name) or [])
        if not isinstance(rows, list):
            rows = []
        results = [_normalize_weaviate_query_result(item) for item in rows if isinstance(item, dict)]
        return {
            "index": index_name,
            "query": query_text,
            "top_k": top_k,
            "results": results,
        }

    def _graphql_url(self) -> str:
        endpoint_url = str(self.vector_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + "/v1/graphql"


class QdrantVectorStoreRuntimeClient(VectorStoreRuntimeClient):
    def query(
        self,
        *,
        index_name: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
        query_text: str | None = None,
    ) -> dict[str, Any]:
        collection_name = _coerce_qdrant_collection_name(index_name)
        payload, status_code = http_json_request(
            self._search_url(collection_name),
            method="POST",
            payload={
                "vector": embedding,
                "limit": top_k,
                "filter": {"must": _qdrant_filter_conditions(filters)},
                "with_payload": True,
                "with_vector": False,
            },
        )
        if payload is None:
            error_code = "vector_runtime_timeout" if status_code == 504 else "vector_runtime_unreachable"
            raise VectorStoreRuntimeClientError(
                code=error_code,
                message="Vector runtime unavailable",
                status_code=status_code,
                details={"provider_slug": self.vector_binding.get("slug"), "status_code": status_code},
            )
        if not 200 <= status_code < 300:
            error_code = (
                "vector_runtime_timeout"
                if status_code == 504
                else "vector_runtime_upstream_unavailable"
                if status_code >= 502
                else "vector_runtime_request_failed"
            )
            raise VectorStoreRuntimeClientError(
                code=error_code,
                message="Vector runtime request failed",
                status_code=status_code,
                details={
                    "provider_slug": self.vector_binding.get("slug"),
                    "status_code": status_code,
                    "upstream": payload,
                },
            )
        points = payload.get("result") if isinstance(payload.get("result"), list) else []
        return {
            "index": index_name,
            "query": query_text,
            "top_k": top_k,
            "results": [_normalize_qdrant_query_result(item) for item in points if isinstance(item, dict)],
        }

    def _scroll_url(self, collection_name: str) -> str:
        endpoint_url = str(self.vector_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + f"/collections/{collection_name}/points/scroll"

    def _search_url(self, collection_name: str) -> str:
        endpoint_url = str(self.vector_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + f"/collections/{collection_name}/points/search"


class OpenAICompatibleEmbeddingsRuntimeClient(EmbeddingsRuntimeClient):
    def embed_texts(
        self,
        *,
        texts: list[str],
    ) -> dict[str, Any]:
        payload = {
            "model": _resolve_effective_embedding_model(self.embeddings_binding),
            "input": texts,
        }
        response_payload, status_code = http_json_request(
            self._embeddings_url(),
            method="POST",
            payload=payload,
        )
        if response_payload is None:
            raise EmbeddingsRuntimeClientError(
                code="embeddings_runtime_unreachable",
                message="Embeddings runtime unavailable",
                status_code=status_code,
                details={"provider_slug": self.embeddings_binding.get("slug"), "status_code": status_code},
            )
        if not 200 <= status_code < 300:
            error_code = (
                "embeddings_runtime_timeout"
                if status_code == 504
                else "embeddings_runtime_upstream_unavailable"
                if status_code >= 502
                else "embeddings_runtime_request_failed"
            )
            raise EmbeddingsRuntimeClientError(
                code=error_code,
                message="Embeddings runtime request failed",
                status_code=status_code,
                details={
                    "provider_slug": self.embeddings_binding.get("slug"),
                    "status_code": status_code,
                    "upstream": response_payload,
                },
            )

        embeddings = _extract_embeddings(response_payload)
        if not embeddings:
            raise EmbeddingsRuntimeClientError(
                code="embeddings_runtime_request_failed",
                message="Embeddings runtime returned no vectors",
                status_code=502,
                details={
                    "provider_slug": self.embeddings_binding.get("slug"),
                    "status_code": 502,
                    "upstream": response_payload,
                },
            )
        return {
            "embeddings": embeddings,
            "dimension": len(embeddings[0]) if embeddings else 0,
            "status_code": status_code,
            "requested_model": payload["model"],
        }

    def _embeddings_url(self) -> str:
        config = self.embeddings_binding.get("config") if isinstance(self.embeddings_binding.get("config"), dict) else {}
        embeddings_path = str(config.get("embeddings_path", "/v1/embeddings")).strip() or "/v1/embeddings"
        endpoint_url = str(self.embeddings_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + embeddings_path


def build_llm_runtime_client(platform_runtime: dict[str, Any]) -> LlmRuntimeClient:
    deployment_profile, capabilities = _coerce_platform_runtime(
        platform_runtime,
        error_cls=LlmRuntimeClientError,
    )
    llm_binding = capabilities.get("llm_inference")
    if not isinstance(llm_binding, dict):
        raise LlmRuntimeClientError(
            code="missing_llm_runtime",
            message="platform_runtime is missing llm_inference binding",
            status_code=500,
        )
    adapter_kind = str(llm_binding.get("adapter_kind", "")).strip().lower()
    if adapter_kind != "openai_compatible_llm":
        raise LlmRuntimeClientError(
            code="unsupported_adapter_kind",
            message="Unsupported LLM runtime adapter",
            status_code=500,
            details={"adapter_kind": adapter_kind},
        )
    return OpenAICompatibleLlmRuntimeClient(deployment_profile=deployment_profile, llm_binding=llm_binding)


def build_embeddings_runtime_client(platform_runtime: dict[str, Any]) -> EmbeddingsRuntimeClient:
    deployment_profile, capabilities = _coerce_platform_runtime(
        platform_runtime,
        error_cls=EmbeddingsRuntimeClientError,
    )
    embeddings_binding = capabilities.get("embeddings")
    if not isinstance(embeddings_binding, dict):
        raise EmbeddingsRuntimeClientError(
            code="missing_embeddings_runtime",
            message="platform_runtime is missing embeddings binding",
            status_code=500,
        )
    adapter_kind = str(embeddings_binding.get("adapter_kind", "")).strip().lower()
    if adapter_kind != "openai_compatible_embeddings":
        raise EmbeddingsRuntimeClientError(
            code="unsupported_adapter_kind",
            message="Unsupported embeddings runtime adapter",
            status_code=500,
            details={"adapter_kind": adapter_kind},
        )
    return OpenAICompatibleEmbeddingsRuntimeClient(
        deployment_profile=deployment_profile,
        embeddings_binding=embeddings_binding,
    )


def build_vector_store_runtime_client(platform_runtime: dict[str, Any]) -> VectorStoreRuntimeClient:
    deployment_profile, capabilities = _coerce_platform_runtime(
        platform_runtime,
        error_cls=VectorStoreRuntimeClientError,
    )
    vector_binding = capabilities.get("vector_store")
    if not isinstance(vector_binding, dict):
        raise VectorStoreRuntimeClientError(
            code="missing_vector_runtime",
            message="platform_runtime is missing vector_store binding",
            status_code=500,
        )
    adapter_kind = str(vector_binding.get("adapter_kind", "")).strip().lower()
    if adapter_kind == "weaviate_http":
        return WeaviateVectorStoreRuntimeClient(deployment_profile=deployment_profile, vector_binding=vector_binding)
    if adapter_kind == "qdrant_http":
        return QdrantVectorStoreRuntimeClient(deployment_profile=deployment_profile, vector_binding=vector_binding)
    raise VectorStoreRuntimeClientError(
        code="unsupported_adapter_kind",
        message="Unsupported vector runtime adapter",
        status_code=500,
        details={"adapter_kind": adapter_kind},
    )


def http_json_request(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | None, int]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = dumps(payload).encode("utf-8")

    request = Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return (loads(raw) if raw else {}), int(response.status)
    except TimeoutError:
        return None, 504
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = loads(raw) if raw else {"error": "upstream_error"}
        except ValueError:
            parsed = {"error": "upstream_error", "body": raw}
        return parsed, int(exc.code)
    except URLError:
        return None, 502


def _coerce_platform_runtime(
    platform_runtime: dict[str, Any],
    *,
    error_cls: type[LlmRuntimeClientError] | type[VectorStoreRuntimeClientError] | type[EmbeddingsRuntimeClientError],
) -> tuple[dict[str, Any], dict[str, Any]]:
    deployment_profile = platform_runtime.get("deployment_profile")
    capabilities = platform_runtime.get("capabilities")
    if not isinstance(deployment_profile, dict) or not isinstance(capabilities, dict):
        raise error_cls(
            code="invalid_platform_runtime",
            message="platform_runtime is missing deployment profile or capabilities",
            status_code=500,
        )
    return deployment_profile, capabilities


def _resolve_effective_model(requested_model: str | None, llm_binding: dict[str, Any]) -> str:
    config = llm_binding.get("config") if isinstance(llm_binding.get("config"), dict) else {}
    explicit_model = str(requested_model or "").strip()
    if explicit_model:
        return explicit_model
    forced_model = str(config.get("forced_model_id", "")).strip()
    if forced_model:
        return forced_model
    fallback_model = str(config.get("local_fallback_model_id", "")).strip()
    if fallback_model:
        return fallback_model
    raise LlmRuntimeClientError(
        code="missing_model_ref",
        message="No model was resolved for execution",
        status_code=500,
        details={"provider_slug": llm_binding.get("slug")},
    )


def _build_request_payload(llm_binding: dict[str, Any], model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    config = llm_binding.get("config") if isinstance(llm_binding.get("config"), dict) else {}
    request_format = str(config.get("request_format", "responses_api")).strip().lower() or "responses_api"
    if request_format == "openai_chat":
        return {
            "model": model,
            "messages": _coerce_openai_chat_messages(messages),
        }
    return {
        "model": model,
        "input": messages,
    }


def _coerce_openai_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        if not role:
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            normalized.append({"role": role, "content": content.strip()})
            continue
        if not isinstance(content, list):
            continue
        text_parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if str(part.get("type", "")).strip().lower() != "text":
                continue
            text = str(part.get("text", "")).strip()
            if text:
                text_parts.append(text)
        if text_parts:
            normalized.append({"role": role, "content": "\n".join(text_parts)})
    return normalized


def _extract_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if str(part.get("type", "")).strip().lower() != "text":
                    continue
                text = str(part.get("text", "")).strip()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
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


def _coerce_weaviate_class_name(index_name: str) -> str:
    parts = [segment for segment in "".join(ch if ch.isalnum() else " " for ch in index_name).split() if segment]
    if not parts:
        raise VectorStoreRuntimeClientError(
            code="invalid_index_name",
            message="index name must contain letters or numbers",
            status_code=400,
        )
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _coerce_metadata_key(key: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in key.strip())
    if not normalized or not normalized[0].isalpha():
        raise VectorStoreRuntimeClientError(
            code="invalid_metadata_key",
            message="metadata keys must start with a letter",
            status_code=400,
        )
    return normalized.lower()


def _build_weaviate_query_operation(
    *,
    class_name: str,
    embedding: list[float],
    top_k: int,
    filters: dict[str, Any],
) -> dict[str, str]:
    args: list[str] = [f"limit: {top_k}", f"nearVector: {{ vector: {_graphql_list(embedding)} }}"]
    if filters:
        args.append(f"where: {_graphql_where_filter(filters)}")
    args_text = ", ".join(args)
    query = (
        "{ Get { "
        f'{class_name}({args_text}) {{ document_id text metadata_json _additional {{ id score }} }} '
        "} } }"
    )
    return {"query": query, "score_kind": "similarity"}


def _graphql_string(value: str) -> str:
    return dumps(value)


def _graphql_list(values: list[float]) -> str:
    return "[" + ", ".join(format(float(value), ".12g") for value in values) + "]"


def _graphql_where_filter(filters: dict[str, Any]) -> str:
    operands: list[str] = []
    for key, value in filters.items():
        property_name = _coerce_metadata_key(str(key))
        if isinstance(value, bool):
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueBoolean: {str(value).lower()} }}')
        elif isinstance(value, int) and not isinstance(value, bool):
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueInt: {value} }}')
        elif isinstance(value, float):
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueNumber: {format(value, ".12g")} }}')
        else:
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueText: {_graphql_string(str(value))} }}')
    if len(operands) == 1:
        return operands[0]
    return "{ operator: And, operands: [" + ", ".join(operands) + "] }"


def _normalize_weaviate_query_result(item: dict[str, Any]) -> dict[str, Any]:
    additional = item.get("_additional")
    additional = additional if isinstance(additional, dict) else {}
    metadata_json = str(item.get("metadata_json", "")).strip()
    try:
        metadata = loads(metadata_json) if metadata_json else {}
    except ValueError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "id": str(item.get("document_id") or additional.get("id") or "").strip(),
        "text": str(item.get("text", "")).strip(),
        "metadata": metadata,
        "score": float(additional.get("score", 0.0) or 0.0),
        "score_kind": "similarity",
    }


def _coerce_qdrant_collection_name(index_name: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in index_name.strip())
    normalized = normalized.strip("_-")
    if not normalized:
        raise VectorStoreRuntimeClientError(
            code="invalid_index_name",
            message="index name must contain letters or numbers",
            status_code=400,
        )
    return normalized.lower()


def _qdrant_filter_conditions(filters: dict[str, Any]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for key, value in filters.items():
        conditions.append({"key": _coerce_metadata_key(str(key)), "match": {"value": value}})
    return conditions


def _normalize_qdrant_query_result(item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    if not metadata:
        for key, value in payload.items():
            if key in {"document_id", "text", "metadata"}:
                continue
            metadata[key] = value
    raw_score = item.get("score")
    score = float(raw_score if isinstance(raw_score, (int, float)) else 1.0)
    return {
        "id": str(payload.get("document_id") or item.get("id") or "").strip(),
        "text": str(payload.get("text", "")).strip(),
        "metadata": metadata,
        "score": score,
        "score_kind": "similarity",
    }


def _resolve_effective_embedding_model(embeddings_binding: dict[str, Any]) -> str:
    config = embeddings_binding.get("config") if isinstance(embeddings_binding.get("config"), dict) else {}
    forced_model = str(config.get("forced_model_id", "")).strip()
    if forced_model:
        return forced_model
    fallback_model = str(config.get("local_fallback_model_id", "")).strip()
    if fallback_model:
        return fallback_model
    raise EmbeddingsRuntimeClientError(
        code="missing_model_ref",
        message="No embedding model was resolved for execution",
        status_code=500,
        details={"provider_slug": embeddings_binding.get("slug")},
    )


def _extract_embeddings(payload: dict[str, Any]) -> list[list[float]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    embeddings: list[list[float]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_embedding = item.get("embedding")
        if not isinstance(raw_embedding, list):
            continue
        vector: list[float] = []
        for value in raw_embedding:
            if isinstance(value, bool):
                vector = []
                break
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                vector = []
                break
        if vector:
            embeddings.append(vector)
    return embeddings
