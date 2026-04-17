from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from json import dumps, loads
import logging
import os
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .openai_compatible_generation import add_openai_compatible_chat_generation_options
from .platform_types import PlatformControlPlaneError, ProviderBinding

_DEFAULT_HTTP_TIMEOUT_SECONDS = 2.0
logger = logging.getLogger(__name__)


class StreamRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def http_json_request(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[Any, int]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = dumps(payload).encode("utf-8")

    normalized_url = str(url or "").strip()
    if not normalized_url or normalized_url.lower() in {"none", "null"} or "://" not in normalized_url:
        return {"error": "invalid_url", "message": "Provider URL is missing or invalid"}, 400

    req = Request(normalized_url, data=data, headers=request_headers, method=method.upper())
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}, int(response.status)
            try:
                return loads(raw), int(response.status)
            except ValueError:
                return {
                    "error": "invalid_json",
                    "message": "Provider returned a non-JSON response",
                    "body": raw[:500],
                    "upstream_status_code": int(response.status),
                }, 502
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


def stream_sse_request(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> Iterator[tuple[str, dict[str, Any]]]:
    request_headers = {"Accept": "text/event-stream"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = dumps(payload).encode("utf-8")

    req = Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            yield from _iter_sse_events(response)
    except TimeoutError as exc:
        raise StreamRequestError(
            "Upstream stream request timed out",
            status_code=504,
        ) from exc
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = loads(raw) if raw else {"error": "upstream_error"}
        except ValueError:
            parsed = {"error": "upstream_error", "body": raw}
        raise StreamRequestError(
            str(parsed.get("message") or parsed.get("error") or "Upstream stream request failed"),
            status_code=int(exc.code),
            payload=parsed,
        ) from exc
    except URLError as exc:
        raise StreamRequestError(
            "Upstream stream request failed",
            status_code=502,
        ) from exc


def _binding_timeout_seconds(config: dict[str, Any]) -> float:
    raw_timeout = config.get("request_timeout_seconds", _DEFAULT_HTTP_TIMEOUT_SECONDS)
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError):
        return _DEFAULT_HTTP_TIMEOUT_SECONDS
    return timeout_seconds if timeout_seconds > 0 else _DEFAULT_HTTP_TIMEOUT_SECONDS


def _binding_secret_refs(binding: ProviderBinding) -> dict[str, str]:
    secret_refs = binding.config.get("secret_refs")
    return dict(secret_refs) if isinstance(secret_refs, dict) else {}


def _resolve_secret_ref(reference: str) -> str | None:
    normalized_reference = reference.strip()
    if not normalized_reference:
        return None
    if normalized_reference.startswith("env://"):
        env_name = normalized_reference.removeprefix("env://").strip()
        return os.getenv(env_name, "").strip() or None
    return normalized_reference


def _openai_compatible_headers(binding: ProviderBinding) -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key_ref = _binding_secret_refs(binding).get("api_key")
    if not api_key_ref:
        return headers
    api_key = _resolve_secret_ref(api_key_ref)
    if not api_key:
        raise PlatformControlPlaneError(
            "provider_secret_missing",
            "Provider secret ref could not be resolved",
            status_code=409,
            details={"provider": binding.provider_slug, "secret_ref": api_key_ref},
        )
    headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _normalized_optional_identifier(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.lower() in {"none", "null"}:
        return None
    return normalized


def _default_resource_runtime_identifier(binding: ProviderBinding) -> str:
    resource = binding.default_resource or {}
    provider_resource_id = _normalized_optional_identifier(resource.get("provider_resource_id"))
    if provider_resource_id:
        return provider_resource_id
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    provider_model_id = _normalized_optional_identifier(metadata.get("provider_model_id"))
    local_path = _normalized_optional_identifier(metadata.get("local_path"))
    source_id = _normalized_optional_identifier(metadata.get("source_id"))
    return provider_model_id or local_path or source_id


def _normalize_model_resource(item: dict[str, Any]) -> dict[str, Any]:
    resource_id = str(item.get("id", "")).strip()
    metadata = {
        "name": item.get("name") or item.get("id"),
        "provider_model_id": str(item.get("id", "")).strip() or None,
        "source_id": str(item.get("source_id", "")).strip() or None,
        "owned_by": item.get("owned_by"),
    }
    return {
        "id": resource_id,
        "resource_kind": "model",
        "ref_type": "provider_resource",
        "managed_model_id": None,
        "provider_resource_id": resource_id or None,
        "display_name": item.get("id") or item.get("name"),
        "metadata": {key: value for key, value in metadata.items() if value not in {None, ""}},
    }


def _filter_models_payload_by_capability(
    binding: ProviderBinding,
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    items = payload.get("data")
    if not isinstance(items, list):
        return payload
    filtered: list[dict[str, Any]] = []
    capability_key = str(binding.capability_key).strip().lower()
    for item in items:
        if not isinstance(item, dict):
            continue
        capabilities = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
        include_item = True
        if capability_key == "llm_inference":
            include_item = bool(capabilities.get("text"))
        elif capability_key == "embeddings":
            include_item = bool(capabilities.get("embeddings"))
        if include_item:
            filtered.append(dict(item))
    return {**payload, "data": filtered}


class LlmInferenceAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError

    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        payload, status_code = self.list_models()
        items = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), list) else []
        resources = [_normalize_model_resource(item) for item in items if isinstance(item, dict)]
        return resources, status_code

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

    @abstractmethod
    def chat_completion_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
        temperature: float | None,
        allow_local_fallback: bool,
    ) -> Iterator[dict[str, Any]]:
        raise NotImplementedError


class EmbeddingsAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError

    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        payload, status_code = self.list_models()
        items = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), list) else []
        resources = [_normalize_model_resource(item) for item in items if isinstance(item, dict)]
        return resources, status_code

    @abstractmethod
    def embed_texts(
        self,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError


class VectorStoreAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
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

    @abstractmethod
    def delete_index(self, *, index_name: str) -> dict[str, Any]:
        raise NotImplementedError


class SandboxExecutionAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        *,
        code: str,
        language: str,
        input_payload: Any,
        timeout_seconds: int,
        policy: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError

    @abstractmethod
    def execute_dry_run(self) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError


class McpRuntimeAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def invoke(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        request_metadata: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError


class OpenAICompatibleLlmAdapter(LlmInferenceAdapter):
    def _request_headers(self) -> dict[str, str]:
        return _openai_compatible_headers(self.binding)

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

    def _request_timeout_seconds(self) -> float:
        return _binding_timeout_seconds(self.binding.config)

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(
            self._health_url(),
            method="GET",
            headers=self._request_headers(),
            timeout_seconds=self._request_timeout_seconds(),
        )
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def list_models(self) -> tuple[dict[str, Any] | None, int]:
        payload, status_code = http_json_request(
            self._models_url(),
            method="GET",
            headers=self._request_headers(),
            timeout_seconds=self._request_timeout_seconds(),
        )
        return _filter_models_payload_by_capability(self.binding, payload if isinstance(payload, dict) else None), status_code

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
        temperature: float | None,
        allow_local_fallback: bool,
    ) -> tuple[dict[str, Any] | None, int]:
        effective_model = model or str(self.binding.config.get("forced_model_id", "")).strip()
        payload = self.build_chat_completion_payload(
            model=effective_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        response_payload, status_code = http_json_request(
            self._chat_url(),
            method="POST",
            payload=payload,
            headers=self._request_headers(),
            timeout_seconds=self._request_timeout_seconds(),
        )
        fallback_model_id = str(self.binding.config.get("local_fallback_model_id", "")).strip()
        if (
            allow_local_fallback
            and fallback_model_id
            and status_code in {400, 404}
            and effective_model != fallback_model_id
            and _is_model_not_found(response_payload)
        ):
            logger.warning(
                "LLM adapter falling back to local model alias '%s' after '%s' returned model_not_found via provider '%s'.",
                fallback_model_id,
                effective_model,
                self.binding.provider_slug,
            )
            fallback_payload = self._build_chat_payload(model=fallback_model_id, messages=messages)
            add_openai_compatible_chat_generation_options(
                fallback_payload,
                model=fallback_model_id,
                request_format=self._request_format(),
                token_budget=max_tokens,
                temperature=temperature,
            )
            fallback_response, fallback_status = http_json_request(
                self._chat_url(),
                method="POST",
                payload=fallback_payload,
                headers=self._request_headers(),
                timeout_seconds=self._request_timeout_seconds(),
            )
            return _normalize_chat_response_payload(fallback_response), fallback_status
        return _normalize_chat_response_payload(response_payload), status_code

    def chat_completion_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
        temperature: float | None,
        allow_local_fallback: bool,
    ) -> Iterator[dict[str, Any]]:
        effective_model = model or str(self.binding.config.get("forced_model_id", "")).strip()
        request_format = self._request_format()
        payload = self.build_chat_completion_payload(
            model=effective_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        payload["stream"] = True

        fallback_model_id = str(self.binding.config.get("local_fallback_model_id", "")).strip()

        def _stream_attempt(stream_payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
            raw_events = stream_sse_request(
                self._chat_url(),
                method="POST",
                payload=stream_payload,
                headers=self._request_headers(),
                timeout_seconds=self._request_timeout_seconds(),
            )
            if request_format == "openai_chat":
                yield from _iter_openai_chat_stream_events(raw_events)
                return
            yield from _iter_vanessa_chat_stream_events(raw_events)

        first_attempt_started = False
        try:
            for event in _stream_attempt(payload):
                event_type = str(event.get("type", "")).strip().lower()
                if event_type == "error":
                    should_retry_fallback = (
                        allow_local_fallback
                        and fallback_model_id
                        and effective_model != fallback_model_id
                        and not first_attempt_started
                        and _is_model_not_found(_stream_error_payload(event))
                    )
                    if should_retry_fallback:
                        logger.warning(
                            "LLM adapter falling back to local model alias '%s' after streamed request for '%s' reported model_not_found via provider '%s'.",
                            fallback_model_id,
                            effective_model,
                            self.binding.provider_slug,
                        )
                        break
                    yield event
                    return
                if event_type == "delta":
                    first_attempt_started = True
                yield event
                if event_type == "complete":
                    return
        except StreamRequestError as exc:
            if (
                allow_local_fallback
                and fallback_model_id
                and effective_model != fallback_model_id
                and _is_model_not_found(exc.payload)
            ):
                logger.warning(
                    "LLM adapter falling back to local model alias '%s' after streamed request for '%s' returned model_not_found via provider '%s'.",
                    fallback_model_id,
                    effective_model,
                    self.binding.provider_slug,
                )
            else:
                yield {
                    "type": "error",
                    "payload": exc.payload or {"error": "llm_stream_unreachable", "message": str(exc)},
                    "status_code": exc.status_code,
                }
                return
        else:
            return

        fallback_payload = self._build_chat_payload(model=fallback_model_id, messages=messages)
        add_openai_compatible_chat_generation_options(
            fallback_payload,
            model=fallback_model_id,
            request_format=request_format,
            token_budget=max_tokens,
            temperature=temperature,
        )
        fallback_payload["stream"] = True
        try:
            yield from _stream_attempt(fallback_payload)
        except StreamRequestError as exc:
            yield {
                "type": "error",
                "payload": exc.payload or {"error": "llm_stream_unreachable", "message": str(exc)},
                "status_code": exc.status_code,
            }

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

    def build_chat_completion_payload(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        request_format = self._request_format()
        payload = self._build_chat_payload(model=model, messages=messages)
        add_openai_compatible_chat_generation_options(
            payload,
            model=model,
            request_format=request_format,
            token_budget=max_tokens,
            temperature=temperature,
        )
        return payload


def build_credential_openai_compatible_llm_adapter(
    *,
    api_base_url: str,
    api_key: str,
    provider_slug: str,
    timeout_seconds: float,
) -> OpenAICompatibleLlmAdapter:
    return OpenAICompatibleLlmAdapter(
        ProviderBinding(
            capability_key="llm_inference",
            provider_instance_id="modelops-credential",
            provider_slug=provider_slug,
            provider_key="openai_compatible_cloud_llm",
            provider_display_name=provider_slug,
            provider_description="Credential-backed OpenAI-compatible LLM",
            endpoint_url=api_base_url.rstrip("/"),
            healthcheck_url=None,
            enabled=True,
            adapter_kind="openai_compatible_llm",
            config={
                "chat_completion_path": "/chat/completions",
                "models_path": "/models",
                "request_format": "openai_chat",
                "request_timeout_seconds": timeout_seconds,
                "secret_refs": {"api_key": api_key},
            },
            binding_config={},
            deployment_profile_id="modelops-credential",
            deployment_profile_slug="modelops-credential",
            deployment_profile_display_name="ModelOps credential",
        )
    )


class OpenAICompatibleEmbeddingsAdapter(EmbeddingsAdapter):
    def _request_headers(self) -> dict[str, str]:
        return _openai_compatible_headers(self.binding)

    def _models_url(self) -> str:
        path = str(self.binding.config.get("models_path", "/v1/models")).strip() or "/v1/models"
        return self.binding.endpoint_url.rstrip("/") + path

    def _embeddings_url(self) -> str:
        path = str(self.binding.config.get("embeddings_path", "/v1/embeddings")).strip() or "/v1/embeddings"
        return self.binding.endpoint_url.rstrip("/") + path

    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self._embeddings_url()

    def _request_timeout_seconds(self) -> float:
        return _binding_timeout_seconds(self.binding.config)

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(
            self._health_url(),
            method="GET",
            headers=self._request_headers(),
            timeout_seconds=self._request_timeout_seconds(),
        )
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def list_models(self) -> tuple[dict[str, Any] | None, int]:
        payload, status_code = http_json_request(
            self._models_url(),
            method="GET",
            headers=self._request_headers(),
            timeout_seconds=self._request_timeout_seconds(),
        )
        return _filter_models_payload_by_capability(self.binding, payload if isinstance(payload, dict) else None), status_code

    def embed_texts(
        self,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> tuple[dict[str, Any] | None, int]:
        effective_model = str(model or "").strip() or _default_resource_runtime_identifier(self.binding)
        if not effective_model:
            raise PlatformControlPlaneError(
                "default_resource_required",
                "Embeddings binding is missing a default resource",
                status_code=409,
                details={"provider": self.binding.provider_slug},
            )
        payload = {
            "model": effective_model,
            "input": texts,
        }
        response_payload, status_code = http_json_request(
            self._embeddings_url(),
            method="POST",
            payload=payload,
            headers=self._request_headers(),
            timeout_seconds=self._request_timeout_seconds(),
        )
        return _normalize_embeddings_response_payload(response_payload), status_code


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

    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        payload, status_code = http_json_request(self._schema_url(), method="GET")
        classes = payload.get("classes") if isinstance(payload, dict) and isinstance(payload.get("classes"), list) else []
        resources = []
        for item in classes:
            if not isinstance(item, dict):
                continue
            class_name = str(item.get("class", "")).strip()
            if not class_name:
                continue
            resources.append(
                {
                    "id": class_name,
                    "resource_kind": "index",
                    "ref_type": "provider_resource",
                    "managed_model_id": None,
                    "provider_resource_id": class_name,
                    "display_name": class_name,
                    "metadata": {},
                }
            )
        return resources, status_code

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

    def delete_index(self, *, index_name: str) -> dict[str, Any]:
        class_name = _coerce_weaviate_class_name(index_name)
        payload, status_code = http_json_request(self._schema_class_url(class_name), method="DELETE")
        if status_code not in {200, 204, 404, 422}:
            _raise_platform_provider_error(
                code="vector_index_delete_failed",
                message="Unable to delete vector index",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        return {
            "index": {
                "name": index_name,
                "provider": self.binding.provider_slug,
                "deleted": status_code not in {404, 422},
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
        if _extract_weaviate_batch_objects(payload) is None:
            _raise_platform_provider_error(
                code="vector_upsert_failed",
                message="Vector document upsert returned an unexpected provider response",
                status_code=502,
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


class QdrantVectorStoreAdapter(VectorStoreAdapter):
    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        path = str(self.binding.config.get("collections_path", "/collections")).strip() or "/collections"
        return self.binding.endpoint_url.rstrip("/") + path

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(self._health_url(), method="GET")
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        payload, status_code = http_json_request(self._collections_url(), method="GET")
        collections = (((payload.get("result") or {}).get("collections")) if isinstance(payload, dict) else [])
        if not isinstance(collections, list):
            collections = []
        resources = []
        for item in collections:
            if not isinstance(item, dict):
                continue
            collection_name = str(item.get("name", "")).strip()
            if not collection_name:
                continue
            resources.append(
                {
                    "id": collection_name,
                    "resource_kind": "collection",
                    "ref_type": "provider_resource",
                    "managed_model_id": None,
                    "provider_resource_id": collection_name,
                    "display_name": collection_name,
                    "metadata": {},
                }
            )
        return resources, status_code

    def ensure_index(self, *, index_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        collection_name = _coerce_qdrant_collection_name(index_name)
        existing_payload, existing_status = http_json_request(self._collection_url(collection_name), method="GET")
        if existing_payload is not None and 200 <= existing_status < 300:
            self._ensure_text_indexes(collection_name=collection_name, schema=schema)
            return {
                "index": {
                    "name": index_name,
                    "provider": self.binding.provider_slug,
                    "status": "ready",
                    "created": False,
                }
            }
        if existing_status not in {404, 502, 504} and existing_payload is not None:
            _raise_platform_provider_error(
                code="vector_index_ensure_failed",
                message="Unable to inspect vector index state",
                status_code=existing_status,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": existing_payload},
            )

        vector_size = _qdrant_vector_size(schema, self.binding.config)
        create_payload = {
            "vectors": {
                "size": vector_size,
                "distance": _qdrant_distance(self.binding.config),
            }
        }
        created_payload, created_status = http_json_request(
            self._collection_url(collection_name),
            method="PUT",
            payload=create_payload,
        )
        if not _qdrant_operation_ok(created_payload, created_status):
            _raise_platform_provider_error(
                code="vector_index_ensure_failed",
                message="Unable to ensure vector index",
                status_code=created_status,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": created_payload},
            )
        self._ensure_text_indexes(collection_name=collection_name, schema=schema)
        return {
            "index": {
                "name": index_name,
                "provider": self.binding.provider_slug,
                "status": "ready",
                "created": True,
            }
        }

    def delete_index(self, *, index_name: str) -> dict[str, Any]:
        collection_name = _coerce_qdrant_collection_name(index_name)
        payload, status_code = http_json_request(self._collection_url(collection_name), method="DELETE")
        if status_code not in {200, 202, 204, 404}:
            _raise_platform_provider_error(
                code="vector_index_delete_failed",
                message="Unable to delete vector index",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        return {
            "index": {
                "name": index_name,
                "provider": self.binding.provider_slug,
                "deleted": status_code != 404,
            }
        }

    def upsert(self, *, index_name: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
        inferred_vector_size = _infer_qdrant_vector_size(documents)
        self.ensure_index(index_name=index_name, schema={"vector_size": inferred_vector_size})
        collection_name = _coerce_qdrant_collection_name(index_name)
        vector_size = inferred_vector_size or int(self.binding.config.get("default_vector_size", 1) or 1)
        payload, status_code = http_json_request(
            self._points_url(collection_name),
            method="PUT",
            payload={
                "points": [
                    {
                        "id": str(document["id"]),
                        "vector": _qdrant_document_vector(document, vector_size=vector_size),
                        "payload": _build_qdrant_payload(document),
                    }
                    for document in documents
                ]
            },
        )
        if not _qdrant_operation_ok(payload, status_code):
            _raise_platform_provider_error(
                code="vector_upsert_failed",
                message="Unable to upsert vector documents",
                status_code=status_code,
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
        collection_name = _coerce_qdrant_collection_name(index_name)
        if embedding is not None:
            payload, status_code = http_json_request(
                self._search_url(collection_name),
                method="POST",
                payload={
                    "vector": embedding,
                    "limit": top_k,
                    "filter": _qdrant_filter(filters),
                    "with_payload": True,
                    "with_vector": False,
                },
            )
            if not _qdrant_result_ok(payload, status_code):
                _raise_platform_provider_error(
                    code="vector_query_failed",
                    message="Unable to query vector index",
                    status_code=status_code,
                    details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
                )
            rows = payload.get("result") if isinstance(payload.get("result"), list) else []
            results = [_normalize_qdrant_query_result(item, score_kind="similarity") for item in rows if isinstance(item, dict)]
            return {"index": index_name, "results": results}

        must_filters = _qdrant_filter_conditions(filters)
        must_filters.append({"key": "text", "match": {"text": str(query_text or "")}})
        payload, status_code = http_json_request(
            self._scroll_url(collection_name),
            method="POST",
            payload={
                "limit": top_k,
                "filter": {"must": must_filters},
                "with_payload": True,
                "with_vector": False,
            },
        )
        if not _qdrant_result_ok(payload, status_code):
            _raise_platform_provider_error(
                code="vector_query_failed",
                message="Unable to query vector index",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        points = (((payload.get("result") or {}).get("points")) if isinstance(payload.get("result"), dict) else [])
        if not isinstance(points, list):
            points = []
        return {
            "index": index_name,
            "results": [_normalize_qdrant_query_result(item, score_kind="text_match") for item in points if isinstance(item, dict)],
        }

    def delete(self, *, index_name: str, ids: list[str]) -> dict[str, Any]:
        collection_name = _coerce_qdrant_collection_name(index_name)
        payload, status_code = http_json_request(
            self._delete_points_url(collection_name),
            method="POST",
            payload={"points": ids},
        )
        if not _qdrant_operation_ok(payload, status_code):
            _raise_platform_provider_error(
                code="vector_delete_failed",
                message="Unable to delete vector documents",
                status_code=status_code,
                details={"index": index_name, "provider": self.binding.provider_slug, "upstream": payload},
            )
        return {
            "index": index_name,
            "count": len(ids),
            "deleted_ids": ids,
        }

    def _collection_url(self, collection_name: str) -> str:
        return self.binding.endpoint_url.rstrip("/") + f"/collections/{collection_name}"

    def _collections_url(self) -> str:
        path = str(self.binding.config.get("collections_path", "/collections")).strip() or "/collections"
        return self.binding.endpoint_url.rstrip("/") + path

    def _points_url(self, collection_name: str) -> str:
        return self._collection_url(collection_name) + "/points"

    def _delete_points_url(self, collection_name: str) -> str:
        return self._collection_url(collection_name) + "/points/delete"

    def _search_url(self, collection_name: str) -> str:
        return self._collection_url(collection_name) + "/points/search"

    def _scroll_url(self, collection_name: str) -> str:
        return self._collection_url(collection_name) + "/points/scroll"

    def _index_url(self, collection_name: str) -> str:
        return self._collection_url(collection_name) + "/index"

    def _ensure_text_indexes(self, *, collection_name: str, schema: dict[str, Any]) -> None:
        for field_name, field_schema in _qdrant_field_indexes(schema).items():
            payload, status_code = http_json_request(
                self._index_url(collection_name),
                method="PUT",
                payload={"field_name": field_name, "field_schema": field_schema},
            )
            if not _qdrant_operation_ok(payload, status_code):
                _raise_platform_provider_error(
                    code="vector_index_ensure_failed",
                    message="Unable to ensure vector index fields",
                    status_code=status_code,
                    details={"provider": self.binding.provider_slug, "upstream": payload, "field_name": field_name},
                )


class HttpSandboxExecutionAdapter(SandboxExecutionAdapter):
    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self.binding.endpoint_url.rstrip("/") + "/health"

    def _execute_url(self) -> str:
        path = str(self.binding.config.get("execute_path", "/v1/execute")).strip() or "/v1/execute"
        return self.binding.endpoint_url.rstrip("/") + path

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(self._health_url(), method="GET")
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def execute(
        self,
        *,
        code: str,
        language: str,
        input_payload: Any,
        timeout_seconds: int,
        policy: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, int]:
        return http_json_request(
            self._execute_url(),
            method="POST",
            payload={
                "code": code,
                "language": language,
                "input": input_payload,
                "timeout_seconds": timeout_seconds,
                "policy": policy,
            },
        )

    def execute_dry_run(self) -> tuple[dict[str, Any] | None, int]:
        return self.execute(
            code=str(self.binding.config.get("dry_run_code", "result = {'status': 'ok'}")),
            language="python",
            input_payload={},
            timeout_seconds=int(self.binding.config.get("default_timeout_seconds", 5) or 5),
            policy={"network_access": False},
        )


class HttpMcpRuntimeAdapter(McpRuntimeAdapter):
    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self.binding.endpoint_url.rstrip("/") + "/health"

    def _invoke_url(self) -> str:
        path = str(self.binding.config.get("invoke_path", "/v1/tools/invoke")).strip() or "/v1/tools/invoke"
        return self.binding.endpoint_url.rstrip("/") + path

    def _tools_url(self) -> str:
        path = str(self.binding.config.get("tools_path", "/v1/tools")).strip() or "/v1/tools"
        return self.binding.endpoint_url.rstrip("/") + path

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(self._health_url(), method="GET")
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def invoke(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        request_metadata: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, int]:
        return http_json_request(
            self._invoke_url(),
            method="POST",
            payload={
                "tool_name": tool_name,
                "arguments": arguments,
                "request_metadata": request_metadata,
            },
        )

    def list_tools(self) -> tuple[dict[str, Any] | None, int]:
        return http_json_request(self._tools_url(), method="GET")


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


def _stream_error_payload(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = event.get("payload")
    if isinstance(payload, dict):
        return payload
    error = event.get("error")
    if isinstance(error, dict):
        return error
    return None


def _iter_openai_chat_stream_events(raw_events: Iterator[tuple[str, dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    text_parts: list[str] = []
    for event_name, event_payload in raw_events:
        if event_name.strip().lower() != "message":
            for normalized_event in _iter_vanessa_chat_stream_events(iter([(event_name, event_payload)])):
                yield normalized_event
                if str(normalized_event.get("type") or "").strip().lower() in {"complete", "error"}:
                    return
            continue
        if str(event_payload.get("raw") or "").strip() == "[DONE]":
            yield _openai_chat_complete_event(text_parts)
            return
        error_payload = event_payload.get("error")
        if isinstance(error_payload, dict):
            yield _stream_error_event(error_payload)
            return
        choice = _first_openai_stream_choice(event_payload)
        if choice is None:
            continue
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str) and content:
                text_parts.append(content)
                yield {"type": "delta", "text": content}
                continue
        if str(choice.get("finish_reason") or "").strip():
            yield _openai_chat_complete_event(text_parts)
            return


def _iter_vanessa_chat_stream_events(raw_events: Iterator[tuple[str, dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    for event_name, event_payload in raw_events:
        normalized_event_name = event_name.strip().lower()
        if normalized_event_name == "delta":
            text = str(event_payload.get("text", ""))
            if text:
                yield {"type": "delta", "text": text}
            continue
        if normalized_event_name == "complete":
            response_payload = event_payload.get("response")
            normalized_response = (
                _normalize_chat_response_payload(response_payload)
                if isinstance(response_payload, dict)
                else None
            )
            yield {
                "type": "complete",
                "response": normalized_response,
                "status_code": 200,
            }
            return
        if normalized_event_name == "error":
            yield _stream_error_event(event_payload)
            return


def _first_openai_stream_choice(event_payload: dict[str, Any]) -> dict[str, Any] | None:
    choices = event_payload.get("choices")
    first_choice = choices[0] if isinstance(choices, list) and choices else None
    return first_choice if isinstance(first_choice, dict) else None


def _openai_chat_complete_event(text_parts: list[str]) -> dict[str, Any]:
    return {
        "type": "complete",
        "response": {
            "output": [
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "".join(text_parts)}],
                }
            ]
        },
        "status_code": 200,
    }


def _stream_error_event(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "error",
        "payload": payload,
        "status_code": _coerce_stream_status_code(payload),
    }


def _coerce_stream_status_code(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("status_code", 502) or 502)
    except (TypeError, ValueError):
        return 502


def _iter_sse_events(response) -> Iterator[tuple[str, dict[str, Any]]]:
    event_name = "message"
    data_lines: list[str] = []

    def _flush() -> tuple[str, dict[str, Any]] | None:
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = "message"
            return None
        raw_data = "\n".join(data_lines)
        data_lines = []
        current_event = event_name
        event_name = "message"
        try:
            payload = loads(raw_data) if raw_data else {}
        except ValueError:
            payload = {"raw": raw_data}
        if not isinstance(payload, dict):
            payload = {"data": payload}
        return current_event, payload

    while True:
        raw_line = response.readline()
        if not raw_line:
            flushed = _flush()
            if flushed is not None:
                yield flushed
            break
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            flushed = _flush()
            if flushed is not None:
                yield flushed
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip() or "message"
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())


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


def _normalize_embeddings_response_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    data = payload.get("data")
    if not isinstance(data, list):
        return payload

    normalized_vectors: list[list[float]] = []
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
            normalized_vectors.append(vector)

    normalized_payload = dict(payload)
    normalized_payload["embeddings"] = normalized_vectors
    normalized_payload["embedding_dimension"] = len(normalized_vectors[0]) if normalized_vectors else 0
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


def _extract_weaviate_batch_objects(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, list):
        return payload if all(isinstance(item, dict) for item in payload) else None
    if not isinstance(payload, dict):
        return None
    objects = payload.get("objects")
    if not isinstance(objects, list):
        return None
    return objects if all(isinstance(item, dict) for item in objects) else None


def _weaviate_batch_has_errors(payload: Any) -> bool:
    objects = _extract_weaviate_batch_objects(payload)
    if objects is None:
        return False
    for item in objects:
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
        "} }"
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


def _coerce_qdrant_collection_name(index_name: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in index_name.strip())
    normalized = normalized.strip("_-")
    if not normalized:
        raise PlatformControlPlaneError("invalid_index_name", "index name must contain letters or numbers", status_code=400)
    return normalized.lower()


def _qdrant_vector_size(schema: dict[str, Any], config: dict[str, Any]) -> int:
    configured = schema.get("vector_size", config.get("default_vector_size", 1))
    if isinstance(configured, bool):
        raise PlatformControlPlaneError("invalid_vector_size", "vector size must be a positive integer", status_code=400)
    try:
        vector_size = int(configured)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError("invalid_vector_size", "vector size must be a positive integer", status_code=400) from exc
    if vector_size <= 0:
        raise PlatformControlPlaneError("invalid_vector_size", "vector size must be a positive integer", status_code=400)
    return vector_size


def _qdrant_distance(config: dict[str, Any]) -> str:
    distance = str(config.get("distance", "Cosine")).strip() or "Cosine"
    return distance[:1].upper() + distance[1:].lower()


def _infer_qdrant_vector_size(documents: list[dict[str, Any]]) -> int | None:
    for document in documents:
        embedding = document.get("embedding")
        if isinstance(embedding, list) and embedding:
            return len(embedding)
    return None


def _qdrant_document_vector(document: dict[str, Any], *, vector_size: int) -> list[float]:
    embedding = document.get("embedding")
    if isinstance(embedding, list) and embedding:
        if len(embedding) != vector_size:
            raise PlatformControlPlaneError(
                "invalid_embedding",
                "embedding size does not match vector index configuration",
                status_code=400,
            )
        return [float(value) for value in embedding]
    return [0.0] * vector_size


def _build_qdrant_payload(document: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(document.get("metadata") or {})
    payload: dict[str, Any] = {
        "document_id": str(document["id"]),
        "text": str(document["text"]),
        "metadata": metadata,
    }
    for key, value in metadata.items():
        payload[_coerce_metadata_key(str(key))] = value
    return payload


def _qdrant_filter(filters: dict[str, Any]) -> dict[str, Any] | None:
    conditions = _qdrant_filter_conditions(filters)
    if not conditions:
        return None
    return {"must": conditions}


def _qdrant_filter_conditions(filters: dict[str, Any]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for key, value in filters.items():
        conditions.append(
            {
                "key": _coerce_metadata_key(str(key)),
                "match": {"value": value},
            }
        )
    return conditions


def _qdrant_operation_ok(payload: dict[str, Any] | None, status_code: int) -> bool:
    if payload is None or not 200 <= status_code < 300:
        return False
    return str(payload.get("status", "")).strip().lower() in {"ok", ""} or payload.get("result") is not None


def _qdrant_result_ok(payload: dict[str, Any] | None, status_code: int) -> bool:
    if payload is None or not 200 <= status_code < 300:
        return False
    return str(payload.get("status", "")).strip().lower() in {"ok", ""} and "result" in payload


def _qdrant_field_indexes(schema: dict[str, Any]) -> dict[str, Any]:
    field_indexes: dict[str, Any] = {
        "text": {
            "type": "text",
            "tokenizer": "word",
            "lowercase": True,
            "phrase_matching": True,
        }
    }
    for item in schema.get("properties", []):
        if not isinstance(item, dict):
            continue
        field_name = _coerce_metadata_key(str(item.get("name", "")))
        if field_name in {"document_id", "text", "metadata_json", "metadata"}:
            continue
        data_type = str(item.get("data_type", "text")).strip().lower() or "text"
        if data_type == "boolean":
            field_indexes[field_name] = "bool"
        elif data_type == "int":
            field_indexes[field_name] = "integer"
        elif data_type == "number":
            field_indexes[field_name] = "float"
        else:
            field_indexes[field_name] = "keyword"
    return field_indexes


def _normalize_qdrant_query_result(item: dict[str, Any], *, score_kind: str) -> dict[str, Any]:
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
        "score_kind": score_kind,
    }


def _raise_platform_provider_error(*, code: str, message: str, status_code: int, details: dict[str, Any]) -> None:
    normalized_status = status_code if 400 <= status_code < 600 else 502
    raise PlatformControlPlaneError(code, message, status_code=normalized_status, details=details)
