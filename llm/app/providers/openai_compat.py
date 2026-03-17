from __future__ import annotations

from json import dumps, loads
from socket import timeout as socket_timeout
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.registry import EmbeddingResult, ProviderResult
from app.schemas import EmbeddingRequest, ImageInputObject, ImageUrlPart, ResponseRequest, TextPart

from .base import ProviderError


def _coerce_openai_message_content(request: ResponseRequest) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in request.input:
        content_parts: list[dict[str, Any]] = []
        text_segments: list[str] = []
        only_text = True
        for part in message.content:
            if isinstance(part, TextPart):
                text_segments.append(part.text)
                content_parts.append({"type": "text", "text": part.text})
            elif isinstance(part, ImageUrlPart):
                only_text = False
                image_url = part.image_url
                if isinstance(image_url, str):
                    content_parts.append({"type": "image_url", "image_url": {"url": image_url}})
                elif isinstance(image_url, ImageInputObject):
                    if image_url.url:
                        content_parts.append({"type": "image_url", "image_url": {"url": image_url.url}})
                    elif image_url.b64_json:
                        data_url = f"data:image/png;base64,{image_url.b64_json}"
                        content_parts.append({"type": "image_url", "image_url": {"url": data_url}})
        if only_text:
            normalized.append({"role": message.role, "content": "\n".join(text_segments)})
        else:
            normalized.append({"role": message.role, "content": content_parts})
    return normalized


def _extract_output_text(body: dict[str, Any]) -> str:
    choices = body.get("choices")
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
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and str(part.get("type", "")).strip().lower() == "text":
                text = str(part.get("text", "")).strip()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)
    return ""


def _extract_embeddings(body: dict[str, Any]) -> list[list[float]]:
    data = body.get("data")
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


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: int,
        auth_header_value: str | None,
        provider_code_prefix: str,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._auth_header_value = auth_header_value
        self._provider_code_prefix = provider_code_prefix

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        payload: dict[str, Any] = {
            "model": upstream_model,
            "messages": _coerce_openai_message_content(request),
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        headers = {"Content-Type": "application/json"}
        if self._auth_header_value:
            headers["Authorization"] = self._auth_header_value

        url = f"{self._base_url}/chat/completions"
        req = Request(url, data=dumps(payload).encode("utf-8"), headers=headers, method="POST")

        try:
            with urlopen(req, timeout=float(self._timeout_seconds)) as response:
                body = response.read().decode("utf-8")
                parsed = loads(body) if body else {}
                usage = parsed.get("usage") if isinstance(parsed, dict) else {}
                prompt_tokens = int(usage.get("prompt_tokens", 0)) if isinstance(usage, dict) else 0
                completion_tokens = (
                    int(usage.get("completion_tokens", 0)) if isinstance(usage, dict) else 0
                )
                return ProviderResult(
                    output_text=_extract_output_text(parsed if isinstance(parsed, dict) else {}),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
        except HTTPError as error:
            body = error.read().decode("utf-8")
            message = "Upstream request failed"
            try:
                parsed_error = loads(body) if body else {}
            except ValueError:
                parsed_error = {}
            if isinstance(parsed_error, dict):
                err = parsed_error.get("error")
                if isinstance(err, dict):
                    message = str(err.get("message", "")).strip() or message
                elif isinstance(err, str) and err.strip():
                    message = err.strip()
            status = int(error.code)
            if status in {401, 403}:
                raise ProviderError(
                    status_code=status,
                    code=f"{self._provider_code_prefix}_auth_error",
                    message=message,
                ) from error
            if status == 429:
                raise ProviderError(
                    status_code=429,
                    code=f"{self._provider_code_prefix}_rate_limited",
                    message=message,
                ) from error
            if status >= 500:
                raise ProviderError(
                    status_code=502,
                    code=f"{self._provider_code_prefix}_unavailable",
                    message=message,
                ) from error
            raise ProviderError(
                status_code=400,
                code=f"{self._provider_code_prefix}_bad_request",
                message=message,
            ) from error
        except (URLError, socket_timeout) as error:
            raise ProviderError(
                status_code=504,
                code=f"{self._provider_code_prefix}_timeout",
                message="Upstream request timed out or network was unreachable.",
            ) from error

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> EmbeddingResult:
        payload: dict[str, Any] = {
            "model": upstream_model,
            "input": request.input,
        }

        headers = {"Content-Type": "application/json"}
        if self._auth_header_value:
            headers["Authorization"] = self._auth_header_value

        url = f"{self._base_url}/embeddings"
        req = Request(url, data=dumps(payload).encode("utf-8"), headers=headers, method="POST")

        try:
            with urlopen(req, timeout=float(self._timeout_seconds)) as response:
                body = response.read().decode("utf-8")
                parsed = loads(body) if body else {}
                usage = parsed.get("usage") if isinstance(parsed, dict) else {}
                prompt_tokens = int(usage.get("prompt_tokens", 0)) if isinstance(usage, dict) else 0
                return EmbeddingResult(
                    embeddings=_extract_embeddings(parsed if isinstance(parsed, dict) else {}),
                    prompt_tokens=prompt_tokens,
                )
        except HTTPError as error:
            body = error.read().decode("utf-8")
            message = "Upstream request failed"
            try:
                parsed_error = loads(body) if body else {}
            except ValueError:
                parsed_error = {}
            if isinstance(parsed_error, dict):
                err = parsed_error.get("error")
                if isinstance(err, dict):
                    message = str(err.get("message", "")).strip() or message
                elif isinstance(err, str) and err.strip():
                    message = err.strip()
            status = int(error.code)
            if status in {401, 403}:
                raise ProviderError(
                    status_code=status,
                    code=f"{self._provider_code_prefix}_auth_error",
                    message=message,
                ) from error
            if status == 429:
                raise ProviderError(
                    status_code=429,
                    code=f"{self._provider_code_prefix}_rate_limited",
                    message=message,
                ) from error
            if status >= 500:
                raise ProviderError(
                    status_code=502,
                    code=f"{self._provider_code_prefix}_unavailable",
                    message=message,
                ) from error
            raise ProviderError(
                status_code=400,
                code=f"{self._provider_code_prefix}_bad_request",
                message=message,
            ) from error
        except (URLError, socket_timeout) as error:
            raise ProviderError(
                status_code=504,
                code=f"{self._provider_code_prefix}_timeout",
                message="Upstream request timed out or network was unreachable.",
            ) from error
