from __future__ import annotations

from abc import ABC, abstractmethod
from json import dumps, loads
from typing import Any
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

    def query(self, *_args, **_kwargs) -> dict[str, Any]:
        raise PlatformControlPlaneError(
            "vector_query_not_implemented",
            "Vector query is not implemented for this adapter yet",
            status_code=501,
        )

    def upsert(self, *_args, **_kwargs) -> dict[str, Any]:
        raise PlatformControlPlaneError(
            "vector_upsert_not_implemented",
            "Vector upsert is not implemented for this adapter yet",
            status_code=501,
        )

    def delete(self, *_args, **_kwargs) -> dict[str, Any]:
        raise PlatformControlPlaneError(
            "vector_delete_not_implemented",
            "Vector delete is not implemented for this adapter yet",
            status_code=501,
        )

    def ensure_index(self, *_args, **_kwargs) -> dict[str, Any]:
        raise PlatformControlPlaneError(
            "vector_index_not_implemented",
            "Vector index management is not implemented for this adapter yet",
            status_code=501,
        )


class OpenAICompatibleLlmAdapter(LlmInferenceAdapter):
    def _chat_url(self) -> str:
        path = str(self.binding.config.get("chat_completion_path", "/v1/chat/completions")).strip() or "/v1/chat/completions"
        return self.binding.endpoint_url.rstrip("/") + path

    def _models_url(self) -> str:
        path = str(self.binding.config.get("models_path", "/v1/models")).strip() or "/v1/models"
        return self.binding.endpoint_url.rstrip("/") + path

    def _health_url(self) -> str:
        if self.binding.healthcheck_url:
            return self.binding.healthcheck_url
        return self.binding.endpoint_url.rstrip("/") + "/health"

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
        payload: dict[str, Any] = {"model": model, "input": messages}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        response_payload, status_code = http_json_request(self._chat_url(), method="POST", payload=payload)
        fallback_model_id = str(self.binding.config.get("local_fallback_model_id", "")).strip()
        if (
            allow_local_fallback
            and fallback_model_id
            and status_code == 404
            and model != fallback_model_id
            and _is_model_not_found(response_payload)
        ):
            fallback_payload = dict(payload)
            fallback_payload["model"] = fallback_model_id
            return http_json_request(self._chat_url(), method="POST", payload=fallback_payload)
        return response_payload, status_code


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


def _is_model_not_found(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("code", "")).strip().lower() == "model_not_found"
    return str(payload.get("error", "")).strip().lower() == "model_not_found"
