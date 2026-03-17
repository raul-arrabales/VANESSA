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
            error_code = "runtime_timeout" if status_code == 504 else "runtime_upstream_unavailable" if status_code >= 502 else "runtime_request_failed"
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


def build_llm_runtime_client(platform_runtime: dict[str, Any]) -> LlmRuntimeClient:
    deployment_profile = platform_runtime.get("deployment_profile")
    capabilities = platform_runtime.get("capabilities")
    if not isinstance(deployment_profile, dict) or not isinstance(capabilities, dict):
        raise LlmRuntimeClientError(
            code="invalid_platform_runtime",
            message="platform_runtime is missing deployment profile or capabilities",
            status_code=500,
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
    return OpenAICompatibleLlmRuntimeClient(
        deployment_profile=deployment_profile,
        llm_binding=llm_binding,
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
