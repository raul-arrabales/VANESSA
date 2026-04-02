from __future__ import annotations

from json import dumps, loads
from typing import Any

from .base import VectorStoreRuntimeClient, VectorStoreRuntimeClientError
from .resolution import binding_timeout_seconds
from .transport import JsonRequestFn, request_json_or_raise


def vector_unavailable_code(status_code: int) -> str:
    return "vector_runtime_timeout" if status_code == 504 else "vector_runtime_unreachable"


def vector_request_failed_code(status_code: int) -> str:
    if status_code == 504:
        return "vector_runtime_timeout"
    if status_code >= 502:
        return "vector_runtime_upstream_unavailable"
    return "vector_runtime_request_failed"


class WeaviateVectorStoreRuntimeClient(VectorStoreRuntimeClient):
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        vector_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, vector_binding=vector_binding)
        self.request_json = request_json

    def query(
        self,
        *,
        index_name: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
        query_text: str | None = None,
    ) -> dict[str, Any]:
        class_name = coerce_weaviate_class_name(index_name)
        operation = build_weaviate_query_operation(
            class_name=class_name,
            embedding=embedding,
            top_k=top_k,
            filters=filters,
        )
        payload, _status_code = request_json_or_raise(
            request_json=self.request_json,
            error_cls=VectorStoreRuntimeClientError,
            binding=self.vector_binding,
            url=self._graphql_url(),
            method="POST",
            payload={"query": operation["query"]},
            timeout_seconds=binding_timeout_seconds(self.vector_binding),
            unavailable_code=vector_unavailable_code,
            unavailable_message="Vector runtime unavailable",
            request_failed_code=vector_request_failed_code,
            request_failed_message="Vector runtime request failed",
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
        results = [normalize_weaviate_query_result(item) for item in rows if isinstance(item, dict)]
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
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        vector_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, vector_binding=vector_binding)
        self.request_json = request_json

    def query(
        self,
        *,
        index_name: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
        query_text: str | None = None,
    ) -> dict[str, Any]:
        collection_name = coerce_qdrant_collection_name(index_name)
        payload, _status_code = request_json_or_raise(
            request_json=self.request_json,
            error_cls=VectorStoreRuntimeClientError,
            binding=self.vector_binding,
            url=self._search_url(collection_name),
            method="POST",
            payload={
                "vector": embedding,
                "limit": top_k,
                "filter": {"must": qdrant_filter_conditions(filters)},
                "with_payload": True,
                "with_vector": False,
            },
            timeout_seconds=binding_timeout_seconds(self.vector_binding),
            unavailable_code=vector_unavailable_code,
            unavailable_message="Vector runtime unavailable",
            request_failed_code=vector_request_failed_code,
            request_failed_message="Vector runtime request failed",
        )
        points = payload.get("result") if isinstance(payload.get("result"), list) else []
        return {
            "index": index_name,
            "query": query_text,
            "top_k": top_k,
            "results": [normalize_qdrant_query_result(item) for item in points if isinstance(item, dict)],
        }

    def _search_url(self, collection_name: str) -> str:
        endpoint_url = str(self.vector_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + f"/collections/{collection_name}/points/search"


def coerce_weaviate_class_name(index_name: str) -> str:
    parts = [segment for segment in "".join(ch if ch.isalnum() else " " for ch in index_name).split() if segment]
    if not parts:
        raise VectorStoreRuntimeClientError(
            code="invalid_index_name",
            message="index name must contain letters or numbers",
            status_code=400,
        )
    return "".join(part[:1].upper() + part[1:] for part in parts)


def coerce_metadata_key(key: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in key.strip())
    if not normalized or not normalized[0].isalpha():
        raise VectorStoreRuntimeClientError(
            code="invalid_metadata_key",
            message="metadata keys must start with a letter",
            status_code=400,
        )
    return normalized.lower()


def build_weaviate_query_operation(
    *,
    class_name: str,
    embedding: list[float],
    top_k: int,
    filters: dict[str, Any],
) -> dict[str, str]:
    args: list[str] = [f"limit: {top_k}", f"nearVector: {{ vector: {graphql_list(embedding)} }}"]
    if filters:
        args.append(f"where: {graphql_where_filter(filters)}")
    args_text = ", ".join(args)
    query = (
        "{ Get { "
        f'{class_name}({args_text}) {{ document_id text metadata_json _additional {{ id score }} }} '
        "} }"
    )
    return {"query": query, "score_kind": "similarity"}


def graphql_string(value: str) -> str:
    return dumps(value)


def graphql_list(values: list[float]) -> str:
    return "[" + ", ".join(format(float(value), ".12g") for value in values) + "]"


def graphql_where_filter(filters: dict[str, Any]) -> str:
    operands: list[str] = []
    for key, value in filters.items():
        property_name = coerce_metadata_key(str(key))
        if isinstance(value, bool):
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueBoolean: {str(value).lower()} }}')
        elif isinstance(value, int) and not isinstance(value, bool):
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueInt: {value} }}')
        elif isinstance(value, float):
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueNumber: {format(value, ".12g")} }}')
        else:
            operands.append(f'{{ path: ["{property_name}"], operator: Equal, valueText: {graphql_string(str(value))} }}')
    if len(operands) == 1:
        return operands[0]
    return "{ operator: And, operands: [" + ", ".join(operands) + "] }"


def normalize_weaviate_query_result(item: dict[str, Any]) -> dict[str, Any]:
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


def coerce_qdrant_collection_name(index_name: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in index_name.strip())
    normalized = normalized.strip("_-")
    if not normalized:
        raise VectorStoreRuntimeClientError(
            code="invalid_index_name",
            message="index name must contain letters or numbers",
            status_code=400,
        )
    return normalized.lower()


def qdrant_filter_conditions(filters: dict[str, Any]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for key, value in filters.items():
        conditions.append({"key": coerce_metadata_key(str(key)), "match": {"value": value}})
    return conditions


def normalize_qdrant_query_result(item: dict[str, Any]) -> dict[str, Any]:
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
