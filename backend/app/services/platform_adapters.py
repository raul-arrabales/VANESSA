from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse, RemoteDisconnected
from json import dumps, loads
import logging
import os
from queue import LifoQueue
from socket import timeout as socket_timeout
from ssl import SSLError
from threading import Lock
from time import monotonic
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from urllib.parse import urlencode, urlparse
from urllib.error import URLError

from .cloud_traffic import endpoint_host_from_url, publish_cloud_traffic_event, request_id_from_headers
from .context_management_metadata import is_internal_metadata_key
from .openai_compatible_generation import (
    add_openai_compatible_chat_generation_options,
    add_openai_compatible_request_options,
)
from .platform_resources import _default_resource_runtime_identifier as _resource_runtime_identifier
from .platform_types import PlatformControlPlaneError, ProviderBinding
from .stream_telemetry import STREAM_DURATION_MEANING_RESPONSE_HEADERS, STREAM_PHASE_RESPONSE_HEADERS

_DEFAULT_HTTP_TIMEOUT_SECONDS = 2.0
_TRACE_RESPONSE_HEADERS = (
    "x-request-id",
    "x-openai-request-id",
    "openai-request-id",
    "request-id",
    "openai-processing-ms",
    "server-timing",
    "cf-ray",
)
logger = logging.getLogger(__name__)
_RETRYABLE_TRANSPORT_ERRORS = (OSError, RemoteDisconnected, SSLError, socket_timeout)
_RESPONSE_DRAIN_ERRORS = (*_RETRYABLE_TRANSPORT_ERRORS, AttributeError)


class StreamRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class _PooledHttpResponse:
    def __init__(
        self,
        response: HTTPResponse,
        *,
        client: "_PooledHttpClient",
        key: tuple[str, str, int],
        connection: HTTPConnection,
    ):
        self._response = response
        self._client = client
        self._key = key
        self._connection = connection
        self.status = int(getattr(response, "status", 0) or 0)
        self.headers = {key.lower(): value for key, value in response.getheaders()}

    def read(self) -> bytes:
        return self._response.read()

    def readline(self) -> bytes:
        return self._response.readline()

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._response.getheader(name, default)

    def __enter__(self) -> "_PooledHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            try:
                self._response.read()
            except _RESPONSE_DRAIN_ERRORS:
                self._client.discard(self._connection)
                return False
            if self._response.isclosed():
                self._client.release(self._key, self._connection)
                return False
        self._client.discard(self._connection)
        return False


class _PooledHttpClient:
    def __init__(self, *, max_idle_per_origin: int = 8):
        self._max_idle_per_origin = max_idle_per_origin
        self._pools: dict[tuple[str, str, int], LifoQueue[HTTPConnection]] = {}
        self._lock = Lock()

    def request(
        self,
        url: str,
        *,
        method: str,
        data: bytes | None,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> _PooledHttpResponse:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise URLError("Provider URL is missing or invalid")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        key = (parsed.scheme, parsed.hostname, port)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        last_error: BaseException | None = None
        for attempt in range(2):
            connection = self._acquire(key, timeout_seconds)
            try:
                connection.request(method.upper(), target, body=data, headers=headers)
                return _PooledHttpResponse(connection.getresponse(), client=self, key=key, connection=connection)
            except _RETRYABLE_TRANSPORT_ERRORS as exc:
                last_error = exc
                self.discard(connection)
                if attempt == 0:
                    continue
                raise URLError(str(exc)) from exc
        raise URLError(str(last_error or "request failed"))

    def _acquire(self, key: tuple[str, str, int], timeout_seconds: float) -> HTTPConnection:
        with self._lock:
            pool = self._pools.setdefault(key, LifoQueue(maxsize=self._max_idle_per_origin))
            while not pool.empty():
                connection = pool.get_nowait()
                connection.timeout = timeout_seconds
                sock = getattr(connection, "sock", None)
                if sock is not None:
                    sock.settimeout(timeout_seconds)
                    return connection
        scheme, host, port = key
        connection_cls = HTTPSConnection if scheme == "https" else HTTPConnection
        return connection_cls(host, port=port, timeout=timeout_seconds)

    def release(self, key: tuple[str, str, int], connection: HTTPConnection) -> None:
        if getattr(connection, "sock", None) is None:
            return
        with self._lock:
            pool = self._pools.setdefault(key, LifoQueue(maxsize=self._max_idle_per_origin))
            if pool.full():
                self.discard(connection)
                return
            pool.put_nowait(connection)

    def discard(self, connection: HTTPConnection) -> None:
        try:
            connection.close()
        except OSError:
            pass


_HTTP_CLIENT = _PooledHttpClient()


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

    try:
        with _HTTP_CLIENT.request(
            normalized_url,
            method=method,
            data=data,
            headers=request_headers,
            timeout_seconds=timeout_seconds,
        ) as response:
            raw = response.read().decode("utf-8")
            if int(response.status) >= 400:
                try:
                    parsed = loads(raw) if raw else {"error": "upstream_error"}
                except ValueError:
                    parsed = {"error": "upstream_error", "body": raw}
                return parsed, int(response.status)
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
    except (TimeoutError, socket_timeout):
        return None, 504
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

    normalized_url = str(url or "").strip()
    started = monotonic()
    try:
        with _HTTP_CLIENT.request(
            normalized_url,
            method=method,
            data=data,
            headers=request_headers,
            timeout_seconds=timeout_seconds,
        ) as response:
            if int(response.status) >= 400:
                raw = response.read().decode("utf-8")
                try:
                    parsed = loads(raw) if raw else {"error": "upstream_error"}
                except ValueError:
                    parsed = {"error": "upstream_error", "body": raw}
                raise StreamRequestError(
                    str(parsed.get("message") or parsed.get("error") or "Upstream stream request failed"),
                    status_code=int(response.status),
                    payload=parsed,
                )
            yield "transport", {
                "phase": STREAM_PHASE_RESPONSE_HEADERS,
                "duration_ms": int((monotonic() - started) * 1000),
                "status_code": int(getattr(response, "status", 0) or 0),
                "endpoint_host": urlparse(normalized_url).netloc,
                "headers": _trace_response_headers(response),
                "duration_meaning": STREAM_DURATION_MEANING_RESPONSE_HEADERS,
            }
            yield from _iter_sse_events(response)
    except (TimeoutError, socket_timeout) as exc:
        raise StreamRequestError(
            "Upstream stream request timed out",
            status_code=504,
        ) from exc
    except URLError as exc:
        raise StreamRequestError(
            "Upstream stream request failed",
            status_code=502,
        ) from exc


def _trace_response_headers(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", None)
    if headers is None:
        return {}
    trace_headers: dict[str, str] = {}
    for header_name in _TRACE_RESPONSE_HEADERS:
        value = None
        get_header = getattr(response, "getheader", None)
        if callable(get_header):
            value = get_header(header_name)
        if value is None:
            get_value = getattr(headers, "get", None)
            value = get_value(header_name) if callable(get_value) else None
        if value:
            trace_headers[header_name] = str(value)[:256]
    return trace_headers


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


def _default_resource_runtime_identifier(binding: ProviderBinding) -> str:
    return _resource_runtime_identifier(binding.default_resource or {})


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


def _binding_reports_cloud_traffic(binding: ProviderBinding) -> bool:
    return str(binding.provider_origin or "").strip().lower() == "cloud"


def _publish_binding_cloud_traffic(
    binding: ProviderBinding,
    *,
    direction: str,
    phase: str,
    operation: str,
    endpoint_url: str,
    status_code: int | None = None,
    duration_ms: int | None = None,
    request_id: str | None = None,
) -> None:
    if not _binding_reports_cloud_traffic(binding):
        return
    publish_cloud_traffic_event(
        {
            "direction": direction,
            "phase": phase,
            "runtime_profile": "online",
            "source_service": "backend",
            "capability": binding.capability_key,
            "operation": operation,
            "provider_origin": binding.provider_origin,
            "provider_key": binding.provider_key,
            "provider_slug": binding.provider_slug,
            "endpoint_host": endpoint_host_from_url(endpoint_url),
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
        }
    )


def _cloud_traced_json_request(
    binding: ProviderBinding,
    url: str,
    *,
    method: str,
    operation: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> tuple[Any, int]:
    if not _binding_reports_cloud_traffic(binding):
        return http_json_request(
            url,
            method=method,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
    started = monotonic()
    _publish_binding_cloud_traffic(
        binding,
        direction="egress",
        phase="request_sent",
        operation=operation,
        endpoint_url=url,
    )
    try:
        response_payload, status_code = http_json_request(
            url,
            method=method,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        _publish_binding_cloud_traffic(
            binding,
            direction="ingress",
            phase="response_failed",
            operation=operation,
            endpoint_url=url,
            duration_ms=int((monotonic() - started) * 1000),
        )
        raise
    _publish_binding_cloud_traffic(
        binding,
        direction="ingress",
        phase="response_received",
        operation=operation,
        endpoint_url=url,
        status_code=status_code,
        duration_ms=int((monotonic() - started) * 1000),
    )
    return response_payload, status_code


def _cloud_traced_sse_request(
    binding: ProviderBinding,
    url: str,
    *,
    method: str,
    operation: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = _DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> Iterator[tuple[str, dict[str, Any]]]:
    if not _binding_reports_cloud_traffic(binding):
        yield from stream_sse_request(
            url,
            method=method,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        return

    started = monotonic()
    _publish_binding_cloud_traffic(
        binding,
        direction="egress",
        phase="request_sent",
        operation=operation,
        endpoint_url=url,
    )
    ingress_emitted = False
    try:
        for event_name, event_payload in stream_sse_request(
            url,
            method=method,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        ):
            if not ingress_emitted and event_name == "transport":
                ingress_emitted = True
                metadata = event_payload if isinstance(event_payload, dict) else {}
                _publish_binding_cloud_traffic(
                    binding,
                    direction="ingress",
                    phase="first_stream_setup",
                    operation=operation,
                    endpoint_url=url,
                    status_code=_safe_int(metadata.get("status_code")),
                    duration_ms=_safe_int(metadata.get("duration_ms")) or int((monotonic() - started) * 1000),
                    request_id=request_id_from_headers(metadata.get("headers") if isinstance(metadata.get("headers"), dict) else None),
                )
            yield event_name, event_payload
    except StreamRequestError as exc:
        if not ingress_emitted:
            _publish_binding_cloud_traffic(
                binding,
                direction="ingress",
                phase="first_stream_setup_failed",
                operation=operation,
                endpoint_url=url,
                status_code=exc.status_code,
                duration_ms=int((monotonic() - started) * 1000),
            )
        raise


def _safe_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


class WebSearchAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def search(self, arguments: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError


class ImageAnalysisAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, *, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        raise NotImplementedError


class ImageGenerationAdapter(ABC):
    def __init__(self, binding: ProviderBinding):
        self.binding = binding

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        raise NotImplementedError

    @abstractmethod
    def generate(self, *, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
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
        payload, status_code = _cloud_traced_json_request(
            self.binding,
            self._health_url(),
            method="GET",
            operation="provider.health",
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
        payload, status_code = _cloud_traced_json_request(
            self.binding,
            self._models_url(),
            method="GET",
            operation="provider.list_models",
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

        response_payload, status_code = _cloud_traced_json_request(
            self.binding,
            self._chat_url(),
            method="POST",
            operation="llm.chat_completion",
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
            add_openai_compatible_request_options(
                fallback_payload,
                config=self.binding.config,
                request_format=self._request_format(),
            )
            fallback_response, fallback_status = _cloud_traced_json_request(
                self.binding,
                self._chat_url(),
                method="POST",
                operation="llm.chat_completion",
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
        add_openai_compatible_request_options(
            payload,
            config=self.binding.config,
            request_format=request_format,
            stream=True,
        )

        fallback_model_id = str(self.binding.config.get("local_fallback_model_id", "")).strip()

        def _stream_attempt(stream_payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
            raw_events = _cloud_traced_sse_request(
                self.binding,
                self._chat_url(),
                method="POST",
                operation="llm.chat_completion_stream",
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
        add_openai_compatible_request_options(
            fallback_payload,
            config=self.binding.config,
            request_format=request_format,
            stream=True,
        )
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
        add_openai_compatible_request_options(
            payload,
            config=self.binding.config,
            request_format=request_format,
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
            provider_origin="cloud",
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
        return self._models_url()

    def _request_timeout_seconds(self) -> float:
        return _binding_timeout_seconds(self.binding.config)

    def health(self) -> dict[str, Any]:
        payload, status_code = _cloud_traced_json_request(
            self.binding,
            self._health_url(),
            method="GET",
            operation="provider.health",
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
        payload, status_code = _cloud_traced_json_request(
            self.binding,
            self._models_url(),
            method="GET",
            operation="provider.list_models",
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
        response_payload, status_code = _cloud_traced_json_request(
            self.binding,
            self._embeddings_url(),
            method="POST",
            operation="embeddings.create",
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
        path = str(self.binding.config.get("tools_path") or self.binding.config.get("list_tools_path") or "/v1/tools").strip() or "/v1/tools"
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


class SearxngWebSearchAdapter(WebSearchAdapter):
    _VALID_TIME_RANGES = {"day", "month", "year"}
    _VALID_SAFESEARCH_VALUES = {"0", "1", "2"}

    def _search_url(self, arguments: dict[str, Any], *, query: str) -> tuple[str | None, dict[str, str] | None]:
        safesearch, error = self._coerce_safesearch(arguments.get("safesearch"))
        if error:
            return None, error
        time_range, error = self._coerce_time_range(arguments.get("time_range"))
        if error:
            return None, error

        language = self._optional_string(arguments.get("language")) or self._optional_string(
            self.binding.config.get("default_language", "")
        )
        categories = self._optional_string(arguments.get("categories")) or self._optional_string(
            self.binding.config.get("default_categories", "")
        )
        engines = self._optional_string(self.binding.config.get("default_engines", ""))
        params: dict[str, str] = {
            "q": query,
            "format": "json",
            "safesearch": safesearch or "1",
        }
        if language:
            params["language"] = language
        if categories:
            params["categories"] = categories
        if engines:
            params["engines"] = engines
        if time_range:
            params["time_range"] = time_range
        return f"{self.binding.endpoint_url.rstrip().rstrip('/')}/search?{urlencode(params)}", None

    def _request_timeout_seconds(self) -> float:
        return _binding_timeout_seconds(self.binding.config)

    def health(self) -> dict[str, Any]:
        payload, status_code = self.search({"query": str(self.binding.config.get("healthcheck_query", "healthcheck")), "top_k": 1})
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def search(self, arguments: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        query = str(arguments.get("query", "")).strip()
        if not query:
            return {"error": "invalid_arguments", "message": "query is required"}, 400
        top_k, error = self._coerce_top_k(arguments.get("top_k", 3))
        if error:
            return error, 400
        assert top_k is not None
        search_url, error = self._search_url(arguments, query=query)
        if error:
            return error, 400
        assert search_url is not None
        payload, status_code = http_json_request(search_url, method="GET", timeout_seconds=self._request_timeout_seconds())
        if payload is None:
            error_code = "search_timeout" if status_code == 504 else "search_backend_unavailable"
            return {"error": error_code, "message": "Search backend is unavailable"}, status_code
        if not 200 <= status_code < 300:
            return {
                "error": "search_backend_error",
                "message": "Search backend returned an error",
                "upstream_status_code": status_code,
                "upstream": payload,
            }, status_code
        return {"query": query, "results": self._normalize_results(payload, top_k=top_k)}, 200

    def _coerce_top_k(self, value: Any) -> tuple[int | None, dict[str, str] | None]:
        try:
            top_k = int(value)
        except (TypeError, ValueError):
            return None, {"error": "invalid_arguments", "message": "top_k must be an integer"}
        return max(1, min(top_k, 10)), None

    def _coerce_safesearch(self, value: Any) -> tuple[str | None, dict[str, str] | None]:
        raw = self._optional_string(value)
        if not raw:
            raw = self._optional_string(self.binding.config.get("default_safesearch", "1"))
        if raw not in self._VALID_SAFESEARCH_VALUES:
            return None, {"error": "invalid_arguments", "message": "safesearch must be one of 0, 1, or 2"}
        return raw, None

    def _coerce_time_range(self, value: Any) -> tuple[str | None, dict[str, str] | None]:
        raw = self._optional_string(value)
        if not raw:
            return None, None
        if raw not in self._VALID_TIME_RANGES:
            return None, {"error": "invalid_arguments", "message": "time_range must be one of day, month, or year"}
        return raw, None

    def _normalize_engine(self, value: Any, result: dict[str, Any]) -> str:
        if isinstance(value, str):
            return value
        engines = result.get("engines")
        if isinstance(engines, list):
            return ", ".join(str(item).strip() for item in engines if str(item).strip())
        return ""

    def _normalize_results(self, payload: dict[str, Any], *, top_k: int) -> list[dict[str, Any]]:
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return []
        normalized: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = self._optional_string(item.get("url"))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            normalized.append(
                {
                    "title": self._optional_string(item.get("title")),
                    "url": url,
                    "snippet": self._optional_string(item.get("content") or item.get("snippet")),
                    "engine": self._normalize_engine(item.get("engine"), item),
                    "rank": len(normalized) + 1,
                }
            )
            if len(normalized) >= top_k:
                break
        return normalized

    def _optional_string(self, value: Any) -> str:
        return str(value).strip() if value is not None else ""


class HttpImageAnalysisAdapter(ImageAnalysisAdapter):
    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self.binding.endpoint_url.rstrip("/") + "/health"

    def _resources_url(self) -> str:
        path = str(self.binding.config.get("resources_path", "/v1/resources")).strip() or "/v1/resources"
        return self.binding.endpoint_url.rstrip("/") + path

    def _analyze_url(self) -> str:
        path = str(self.binding.config.get("analyze_path", "/v1/analyze")).strip() or "/v1/analyze"
        return self.binding.endpoint_url.rstrip("/") + path

    def _request_timeout_seconds(self) -> float:
        return _binding_timeout_seconds(self.binding.config)

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(
            self._health_url(),
            method="GET",
            timeout_seconds=self._request_timeout_seconds(),
        )
        reachable = payload is not None and 200 <= status_code < 300
        return {
            "reachable": reachable,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        payload, status_code = http_json_request(
            self._resources_url(),
            method="GET",
            timeout_seconds=self._request_timeout_seconds(),
        )
        raw_resources = payload.get("resources") if isinstance(payload, dict) else []
        resources: list[dict[str, Any]] = []
        if isinstance(raw_resources, list):
            for item in raw_resources:
                if not isinstance(item, dict):
                    continue
                resource_id = str(item.get("id") or item.get("provider_resource_id") or "").strip()
                if not resource_id:
                    continue
                resources.append(
                    {
                        "id": resource_id,
                        "resource_kind": "model",
                        "ref_type": "provider_resource",
                        "managed_model_id": None,
                        "provider_resource_id": str(item.get("provider_resource_id") or resource_id).strip(),
                        "display_name": item.get("display_name") or resource_id,
                        "metadata": {
                            key: value
                            for key, value in dict(item.get("metadata") or {}).items()
                            if value not in {None, ""}
                        },
                    }
                )
        return resources, status_code

    def analyze(self, *, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        return http_json_request(
            self._analyze_url(),
            method="POST",
            payload=payload,
            timeout_seconds=self._request_timeout_seconds(),
        )


class HttpImageGenerationAdapter(ImageGenerationAdapter):
    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self.binding.endpoint_url.rstrip("/") + "/health"

    def _resources_url(self) -> str:
        path = str(self.binding.config.get("resources_path", "/v1/resources")).strip() or "/v1/resources"
        return self.binding.endpoint_url.rstrip("/") + path

    def _generate_url(self) -> str:
        path = str(self.binding.config.get("generate_path", "/v1/generate")).strip() or "/v1/generate"
        return self.binding.endpoint_url.rstrip("/") + path

    def _request_timeout_seconds(self) -> float:
        return _binding_timeout_seconds(self.binding.config)

    def health(self) -> dict[str, Any]:
        payload, status_code = http_json_request(
            self._health_url(),
            method="GET",
            timeout_seconds=self._request_timeout_seconds(),
        )
        return {
            "reachable": payload is not None and 200 <= status_code < 300,
            "status_code": status_code,
            "provider_key": self.binding.provider_key,
            "provider_slug": self.binding.provider_slug,
        }

    def list_resources(self) -> tuple[list[dict[str, Any]], int]:
        payload, status_code = http_json_request(
            self._resources_url(),
            method="GET",
            timeout_seconds=self._request_timeout_seconds(),
        )
        raw_resources = payload.get("resources") if isinstance(payload, dict) else []
        resources: list[dict[str, Any]] = []
        if isinstance(raw_resources, list):
            for item in raw_resources:
                if not isinstance(item, dict):
                    continue
                resource_id = str(item.get("id") or item.get("provider_resource_id") or "").strip()
                if not resource_id:
                    continue
                resource_kind = str(item.get("resource_kind") or "model").strip().lower() or "model"
                resources.append(
                    {
                        "id": resource_id,
                        "resource_kind": resource_kind,
                        "ref_type": "provider_resource",
                        "managed_model_id": None,
                        "provider_resource_id": str(item.get("provider_resource_id") or resource_id).strip(),
                        "display_name": item.get("display_name") or resource_id,
                        "metadata": {
                            key: value
                            for key, value in dict(item.get("metadata") or {}).items()
                            if value not in {None, ""}
                        },
                    }
                )
        return resources, status_code

    def generate(self, *, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        return http_json_request(
            self._generate_url(),
            method="POST",
            payload=payload,
            timeout_seconds=self._request_timeout_seconds(),
        )


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
    usage_payload: dict[str, Any] | None = None
    for event_name, event_payload in raw_events:
        if event_name.strip().lower() != "message":
            for normalized_event in _iter_vanessa_chat_stream_events(iter([(event_name, event_payload)])):
                yield normalized_event
                if str(normalized_event.get("type") or "").strip().lower() in {"complete", "error"}:
                    return
            continue
        if str(event_payload.get("raw") or "").strip() == "[DONE]":
            yield _openai_chat_complete_event(text_parts, usage=usage_payload)
            return
        if isinstance(event_payload.get("usage"), dict):
            usage_payload = dict(event_payload["usage"])
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
            yield _openai_chat_complete_event(text_parts, usage=usage_payload)
            return


def _iter_vanessa_chat_stream_events(raw_events: Iterator[tuple[str, dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    text_parts: list[str] = []
    for event_name, event_payload in raw_events:
        normalized_event_name = event_name.strip().lower()
        if normalized_event_name == "transport":
            yield {
                "type": "transport",
                **event_payload,
            }
            continue
        if normalized_event_name == "delta":
            text = str(event_payload.get("text", ""))
            if text:
                text_parts.append(text)
                yield {"type": "delta", "text": text}
            continue
        if normalized_event_name == "complete":
            response_payload = event_payload.get("response")
            yield {
                "type": "complete",
                "response": normalize_stream_complete_response(
                    response_payload if isinstance(response_payload, dict) else None,
                    text_parts,
                ),
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


def _openai_chat_complete_event(text_parts: list[str], *, usage: dict[str, Any] | None = None) -> dict[str, Any]:
    response = normalize_stream_complete_response(None, text_parts) or {}
    if usage:
        response["usage"] = usage
    return {
        "type": "complete",
        "response": response,
        "status_code": 200,
    }


def normalize_stream_complete_response(response_payload: dict[str, Any] | None, text_parts: list[str]) -> dict[str, Any] | None:
    normalized_response = _normalize_chat_response_payload(response_payload) if isinstance(response_payload, dict) else None
    if normalized_response is not None:
        return normalized_response
    return {
        "output": [
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "".join(text_parts)}],
            }
        ]
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
        {"name": "page_number", "dataType": ["int"]},
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
        if name in {"document_id", "text", "metadata_json", "page_number"}:
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
        if is_internal_metadata_key(key):
            continue
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
        if is_internal_metadata_key(key):
            continue
        normalized_key = _coerce_metadata_key(str(key))
        payload[normalized_key] = value
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
        "page_number": "integer",
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
        if field_name in {"document_id", "text", "metadata_json", "metadata", "page_number"}:
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
