from __future__ import annotations

from abc import ABC, abstractmethod
from json import dumps, loads
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .platform_types import PlatformControlPlaneError, ProviderBinding

_DEFAULT_HTTP_TIMEOUT_SECONDS = 2.0


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

    req = Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return (loads(raw) if raw else {}), int(response.status)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = loads(raw) if raw else {"error": "upstream_error"}
        except ValueError:
            parsed = {"error": "upstream_error", "body": raw}
        return parsed, int(exc.code)
    except URLError:
        return None, 502


class LlmInferenceAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError

    @abstractmethod
    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
        temperature: float | None,
        allow_local_fallback: bool,
    ) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError


class VectorStoreAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        *,
        index_name: str,
        query_text: str | None,
        embedding: list[float] | None,
        top_k: int,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, *, index_name: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, *, index_name: str, ids: list[str]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def ensure_index(self, *, index_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class OpenAICompatibleLlmAdapter(LlmInferenceAdapter):
    def _request_format(self) -> str:
        return str(self.binding.config.get("request_format", "responses_api")).strip().lower() or "responses_api"

    def _chat_url(self) -> str:
        path = str(self.binding.config.get("chat_completion_path", "/v1/chat/completions")).strip() or "/v1/chat/completions"
        return self.binding.endpoint_url.rstrip("/") + path

    def _models_url(self) -> str:
        path = str(self.binding.config.get("models_path", "/v1/models")).strip() or "/v1/models"
        return self.binding.endpoint_url.rstrip("/") + path

    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self._models_url()

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(self._health_url(), method="GET")
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def list_models(self) -> tuple[dict[str, Any] | None, int]:
        return http_json_request(self._models_url(), method="GET")

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
        temperature: float | None,
        allow_local_fallback: bool,
    ) -> tuple[dict[str, Any] | None, int]:
        effective_model = str(self.binding.config.get("forced_model_id", "")).strip() or model
        payload: dict[str, Any] = self._build_chat_payload(model=effective_model, messages=messages)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        response_payload, status_code = http_json_request(self._chat_url(), method="POST", payload=payload)
        fallback_model_id = str(self.binding.config.get("local_fallback_model_id", "")).strip()
        if (
            allow_local_fallback
            and fallback_model_id
            and status_code in {400, 404}
            and effective_model != fallback_model_id
            and _is_model_not_found(response_payload)
        ):
            fallback_payload = dict(payload)
            fallback_payload["model"] = fallback_model_id
            fallback_response, fallback_status = http_json_request(self._chat_url(), method="POST", payload=fallback_payload)
            return _normalize_chat_response_payload(fallback_response), fallback_status
        return _normalize_chat_response_payload(response_payload), status_code

    def _build_chat_payload(self, *, model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        request_format = self._request_format()
        if request_format == "openai_chat":
            return {
                "model": model,
                "messages": _coerce_openai_chat_messages(messages),
            }
        return {
            "model": model,
            "input": messages,
        }


class WeaviateVectorStoreAdapter(VectorStoreAdapter):
    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self.binding.endpoint_url.rstrip("/") + "/v1/.well-known/ready"

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(self._health_url(), method="GET")
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def ensure_index(self, *, index_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        class_name = _coerce_weaviate_class_name(index_name)
        existing, status_code = http_json_request(self._schema_class_url(class_name), method="GET")
        if existing is not None and 200 <= status_code < 300:
            return {
                "index": {
                    "name": index_name,
                    "provider": self.binding.provider_slug,
                    "status": "ready",
                    "created": False,
                }
            }
        if status_code not in {404, 422, 502} and existing is not None:
            _raise_platform_provider_error(
                code="vector_index_ensure_failed",
                message="Unable to inspect vector index state",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": existing},
            )

        payload = {
            "class": class_name,
            "vectorizer": "none",
            "properties": _build_weaviate_schema_properties(schema),
        }
        created_payload, created_status = http_json_request(self._schema_url(), method="POST", payload=payload)
        if not (200 <= created_status < 300) and not _weaviate_already_exists(created_payload):
            _raise_platform_provider_error(
                code="vector_index_ensure_failed",
                message="Unable to ensure vector index",
                status_code=created_status,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": created_payload},
            )
        return {
            "index": {
                "name": index_name,
                "provider": self.binding.provider_slug,
                "status": "ready",
                "created": 200 <= created_status < 300,
            }
        }

    def upsert(self, *, index_name: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
        self.ensure_index(index_name=index_name, schema={})
        class_name = _coerce_weaviate_class_name(index_name)
        batch_payload = {
            "objects": [
                {
                    "class": class_name,
                    "id": _weaviate_object_uuid(index_name, str(document["id"])),
                    "properties": _build_weaviate_properties(document),
                    **({"vector": document["embedding"]} if document.get("embedding") is not None else {}),
                }
                for document in documents
            ]
        }
        payload, status_code = http_json_request(self._batch_objects_url(), method="POST", payload=batch_payload)
        if payload is None or not 200 <= status_code < 300:
            _raise_platform_provider_error(
                code="vector_upsert_failed",
                message="Unable to upsert vector documents",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        if _weaviate_batch_has_errors(payload):
            _raise_platform_provider_error(
                code="vector_upsert_failed",
                message="Vector document upsert returned provider errors",
                status_code=502,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        return {
            "index": index_name,
            "count": len(documents),
            "documents": [{"id": str(document["id"]), "status": "upserted"} for document in documents],
        }

    def query(
        self,
        *,
        index_name: str,
        query_text: str | None,
        embedding: list[float] | None,
        top_k: int,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        class_name = _coerce_weaviate_class_name(index_name)
        operation = _build_weaviate_query_operation(
            class_name=class_name,
            query_text=query_text,
            embedding=embedding,
            top_k=top_k,
            filters=filters,
        )
        payload, status_code = http_json_request(
            self._graphql_url(),
            method="POST",
            payload={"query": operation["query"]},
        )
        if payload is None or not 200 <= status_code < 300:
            _raise_platform_provider_error(
                code="vector_query_failed",
                message="Unable to query vector index",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        if isinstance(payload.get("errors"), list) and payload["errors"]:
            _raise_platform_provider_error(
                code="vector_query_failed",
                message="Vector query returned provider errors",
                status_code=502,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )

        rows = (((payload.get("data") or {}).get("Get") or {}).get(class_name) or [])
        if not isinstance(rows, list):
            rows = []
        return {
            "index": index_name,
            "results": [_normalize_weaviate_query_result(item, score_kind=operation["score_kind"]) for item in rows if isinstance(item, dict)],
        }

    def delete(self, *, index_name: str, ids: list[str]) -> dict[str, Any]:
        class_name = _coerce_weaviate_class_name(index_name)
        deleted_ids: list[str] = []
        for raw_id in ids:
            payload, status_code = http_json_request(
                self._object_url(class_name, _weaviate_object_uuid(index_name, raw_id)),
                method="DELETE",
            )
            if status_code not in {200, 204, 404}:
                _raise_platform_provider_error(
                    code="vector_delete_failed",
                    message="Unable to delete vector documents",
                    status_code=status_code,
                    details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload, "document_id": raw_id},
                )
            if status_code != 404:
                deleted_ids.append(raw_id)
        return {
            "index": index_name,
            "count": len(deleted_ids),
            "deleted_ids": deleted_ids,
        }

    def _schema_url(self) -> str:
        return self.binding.endpoint_url.rstrip("/") + "/v1/schema"

    def _schema_class_url(self, class_name: str) -> str:
        return self._schema_url().rstrip("/") + f"/{class_name}"

    def _batch_objects_url(self) -> str:
        return self.binding.endpoint_url.rstrip("/") + "/v1/batch/objects"

    def _graphql_url(self) -> str:
        return self.binding.endpoint_url.rstrip("/") + "/v1/graphql"

    def _object_url(self, class_name: str, object_id: str) -> str:
        return self.binding.endpoint_url.rstrip("/") + f"/v1/objects/{class_name}/{object_id}"


def _is_model_not_found(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("code", "")).strip().lower() == "model_not_found"
    error = payload.get("error")
    if isinstance(error, dict):
        error_code = str(error.get("code", "")).strip().lower()
        error_message = str(error.get("message", "")).strip().lower()
        return error_code == "model_not_found" or ("model" in error_message and "not found" in error_message)
    error_text = str(error or "").strip().lower()
    return error_text == "model_not_found" or ("model" in error_text and "not found" in error_text)


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


def _normalize_chat_response_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    if "output" in payload:
        return payload

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return payload

    first = choices[0]
    if not isinstance(first, dict):
        return payload
    message = first.get("message")
    if not isinstance(message, dict):
        return payload

    role = str(message.get("role", "")).strip().lower() or "assistant"
    content = message.get("content")
    normalized_parts: list[dict[str, str]] = []
    if isinstance(content, str):
        text = content.strip()
        if text:
            normalized_parts.append({"type": "text", "text": text})
    elif isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if str(part.get("type", "")).strip().lower() != "text":
                continue
            text = str(part.get("text", "")).strip()
            if text:
                normalized_parts.append({"type": "text", "text": text})

    normalized_payload = dict(payload)
    if normalized_parts:
        normalized_payload["output"] = [
            {
                "role": role,
                "content": normalized_parts,
            }
        ]
    return normalized_payload


def _coerce_weaviate_class_name(index_name: str) -> str:
    parts = [segment for segment in "".join(ch if ch.isalnum() else " " for ch in index_name).split() if segment]
    if not parts:
        raise PlatformControlPlaneError("invalid_index_name", "index name must contain letters or numbers", status_code=400)
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _coerce_metadata_key(key: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in key.strip())
    if not normalized or not normalized[0].isalpha():
        raise PlatformControlPlaneError("invalid_metadata_key", "metadata keys must start with a letter", status_code=400)
    return normalized.lower()


def _build_weaviate_schema_properties(schema: dict[str, Any]) -> list[dict[str, Any]]:
    properties = [
        {"name": "document_id", "dataType": ["text"]},
        {"name": "text", "dataType": ["text"]},
        {"name": "metadata_json", "dataType": ["text"]},
    ]
    raw_properties = schema.get("properties")
    if not isinstance(raw_properties, list):
        return properties

    for item in raw_properties:
        if not isinstance(item, dict):
            continue
        name = _coerce_metadata_key(str(item.get("name", "")))
        data_type = str(item.get("data_type", "text")).strip().lower() or "text"
        if data_type not in {"text", "number", "int", "boolean"}:
            raise PlatformControlPlaneError("invalid_schema_property_type", "Unsupported schema property type", status_code=400)
        if name in {"document_id", "text", "metadata_json"}:
            continue
        properties.append({"name": name, "dataType": [_weaviate_data_type(data_type)]})
    return properties


def _build_weaviate_properties(document: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(document.get("metadata") or {})
    properties: dict[str, Any] = {
        "document_id": str(document["id"]),
        "text": str(document["text"]),
        "metadata_json": dumps(metadata, sort_keys=True),
    }
    for key, value in metadata.items():
        normalized_key = _coerce_metadata_key(str(key))
        if normalized_key in {"document_id", "text", "metadata_json"}:
            continue
        properties[normalized_key] = value
    return properties


def _weaviate_data_type(data_type: str) -> str:
    if data_type == "number":
        return "number"
    if data_type == "int":
        return "int"
    if data_type == "boolean":
        return "boolean"
    return "text"


def _weaviate_object_uuid(index_name: str, document_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"{index_name}:{document_id}"))


def _weaviate_already_exists(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    error = payload.get("error")
    if isinstance(error, list):
        return any("already exists" in str(item.get("message", "")).lower() for item in error if isinstance(item, dict))
    if isinstance(error, dict):
        return "already exists" in str(error.get("message", "")).lower()
    return "already exists" in dumps(payload).lower()


def _weaviate_batch_has_errors(payload: dict[str, Any]) -> bool:
    if payload.get("errors") is False:
        return False
    objects = payload.get("objects")
    if not isinstance(objects, list):
        return False
    for item in objects:
        if not isinstance(item, dict):
            continue
        result = item.get("result")
        if isinstance(result, dict):
            errors = result.get("errors")
            if errors:
                return True
    return False


def _build_weaviate_query_operation(
    *,
    class_name: str,
    query_text: str | None,
    embedding: list[float] | None,
    top_k: int,
    filters: dict[str, Any],
) -> dict[str, str]:
    args: list[str] = [f"limit: {top_k}"]
    if embedding is not None:
        args.append(f"nearVector: {{ vector: {_graphql_list(embedding)} }}")
        score_field = "distance"
        score_kind = "distance"
    else:
        args.append(f'bm25: {{ query: {_graphql_string(query_text or "")}, properties: ["text"] }}')
        score_field = "score"
        score_kind = "bm25"
    if filters:
        args.append(f"where: {_graphql_where_filter(filters)}")
    args_text = ", ".join(args)
    query = (
        "{ Get { "
        f'{class_name}({args_text}) {{ document_id text metadata_json _additional {{ id {score_field} }} }} '
        "} } }"
    )
    return {"query": query, "score_kind": score_kind}


def _graphql_list(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in values) + "]"


def _graphql_string(value: str) -> str:
    return dumps(value)


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


def _normalize_weaviate_query_result(item: dict[str, Any], *, score_kind: str) -> dict[str, Any]:
    additional = item.get("_additional")
    additional = additional if isinstance(additional, dict) else {}
    score_field = "score" if score_kind == "bm25" else score_kind
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
        "score": float(additional.get(score_field, 0.0) or 0.0),
        "score_kind": score_kind,
    }


def _raise_platform_provider_error(*, code: str, message: str, status_code: int, details: dict[str, Any]) -> None:
    normalized_status = status_code if 400 <= status_code < 600 else 502
    raise PlatformControlPlaneError(code, message, status_code=normalized_status, details=details)
