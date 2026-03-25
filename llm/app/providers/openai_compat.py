from __future__ import annotations

from collections.abc import Iterator
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
        if message.role == "assistant" and message.tool_calls:
            normalized.append(
                {
                    "role": "assistant",
                    "content": "\n".join(
                        part.text for part in message.content if isinstance(part, TextPart)
                    ).strip(),
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in message.tool_calls
                    ],
                }
            )
            continue
        if message.role == "tool":
            normalized.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": "\n".join(
                        part.text for part in message.content if isinstance(part, TextPart)
                    ).strip(),
                }
            )
            continue
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


def _extract_tool_calls(body: dict[str, Any]) -> list[dict[str, Any]]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return []
    first = choices[0]
    if not isinstance(first, dict):
        return []
    message = first.get("message")
    if not isinstance(message, dict):
        return []
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in tool_calls:
        if not isinstance(item, dict):
            continue
        function = item.get("function")
        if not isinstance(function, dict):
            continue
        tool_id = str(item.get("id", "")).strip()
        function_name = str(function.get("name", "")).strip()
        arguments = str(function.get("arguments", ""))
        if not tool_id or not function_name:
            continue
        normalized.append(
            {
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": function_name,
                    "arguments": arguments,
                },
            }
        )
    return normalized


def _extract_stream_delta(body: dict[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, dict):
        return ""

    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and str(part.get("type", "")).strip().lower() == "text":
                text = str(part.get("text", ""))
                if text:
                    text_parts.append(text)
        return "".join(text_parts)
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


def _extract_error_details(body: dict[str, Any]) -> tuple[int | None, str | None]:
    object_type = str(body.get("object", "")).strip().lower()
    if object_type == "error":
        raw_code = body.get("code")
        status_code: int | None = None
        if isinstance(raw_code, int):
            status_code = raw_code
        elif isinstance(raw_code, str):
            try:
                status_code = int(raw_code.strip())
            except ValueError:
                status_code = None
        message = str(body.get("message", "")).strip() or "Upstream request failed"
        return status_code, message

    err = body.get("error")
    if isinstance(err, dict):
        message = str(err.get("message", "")).strip() or "Upstream request failed"
        raw_code = err.get("code")
        status_code = raw_code if isinstance(raw_code, int) else None
        return status_code, message
    if isinstance(err, str) and err.strip():
        return None, err.strip()
    return None, None


def _raise_payload_error_if_present(body: dict[str, Any], *, provider_code_prefix: str) -> None:
    status_code, message = _extract_error_details(body)
    if message is None:
        return

    normalized_status = status_code if isinstance(status_code, int) and status_code > 0 else 502
    if normalized_status in {401, 403}:
        code = f"{provider_code_prefix}_auth_error"
    elif normalized_status == 429:
        code = f"{provider_code_prefix}_rate_limited"
    elif normalized_status >= 500:
        normalized_status = 502
        code = f"{provider_code_prefix}_unavailable"
    elif normalized_status == 400:
        code = f"{provider_code_prefix}_bad_request"
    else:
        code = f"{provider_code_prefix}_upstream_error"

    raise ProviderError(
        status_code=normalized_status,
        code=code,
        message=message,
    )


def _iter_sse_data_chunks(response) -> Iterator[str]:
    data_lines: list[str] = []
    while True:
        raw_line = response.readline()
        if not raw_line:
            break
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        yield "\n".join(data_lines)


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

    @property
    def base_url(self) -> str:
        return self._base_url

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        payload: dict[str, Any] = {
            "model": upstream_model,
            "messages": _coerce_openai_message_content(request),
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = [
                {
                    "type": tool.type,
                    "function": {
                        "name": tool.function.name,
                        "description": tool.function.description,
                        "parameters": tool.function.parameters,
                    },
                }
                for tool in request.tools
            ]

        headers = {"Content-Type": "application/json"}
        if self._auth_header_value:
            headers["Authorization"] = self._auth_header_value

        url = f"{self._base_url}/chat/completions"
        req = Request(url, data=dumps(payload).encode("utf-8"), headers=headers, method="POST")

        try:
            with urlopen(req, timeout=float(self._timeout_seconds)) as response:
                body = response.read().decode("utf-8")
                parsed = loads(body) if body else {}
                if isinstance(parsed, dict):
                    _raise_payload_error_if_present(
                        parsed,
                        provider_code_prefix=self._provider_code_prefix,
                    )
                usage = parsed.get("usage") if isinstance(parsed, dict) else {}
                prompt_tokens = int(usage.get("prompt_tokens", 0)) if isinstance(usage, dict) else 0
                completion_tokens = (
                    int(usage.get("completion_tokens", 0)) if isinstance(usage, dict) else 0
                )
                return ProviderResult(
                    output_text=_extract_output_text(parsed if isinstance(parsed, dict) else {}),
                    tool_calls=_extract_tool_calls(parsed if isinstance(parsed, dict) else {}),
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

    def generate_stream(
        self,
        request: ResponseRequest,
        *,
        upstream_model: str,
    ) -> Iterator[dict[str, object]]:
        payload: dict[str, Any] = {
            "model": upstream_model,
            "messages": _coerce_openai_message_content(request),
            "stream": True,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = [
                {
                    "type": tool.type,
                    "function": {
                        "name": tool.function.name,
                        "description": tool.function.description,
                        "parameters": tool.function.parameters,
                    },
                }
                for tool in request.tools
            ]

        headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }
        if self._auth_header_value:
            headers["Authorization"] = self._auth_header_value

        url = f"{self._base_url}/chat/completions"
        req = Request(url, data=dumps(payload).encode("utf-8"), headers=headers, method="POST")

        try:
            with urlopen(req, timeout=float(self._timeout_seconds)) as response:
                prompt_tokens = 0
                completion_tokens = 0
                for chunk in _iter_sse_data_chunks(response):
                    if chunk == "[DONE]":
                        break
                    parsed = loads(chunk) if chunk else {}
                    if not isinstance(parsed, dict):
                        continue
                    usage = parsed.get("usage")
                    if isinstance(usage, dict):
                        prompt_tokens = int(usage.get("prompt_tokens", prompt_tokens) or prompt_tokens)
                        completion_tokens = int(
                            usage.get("completion_tokens", completion_tokens) or completion_tokens
                        )
                    delta_text = _extract_stream_delta(parsed)
                    if delta_text:
                        yield {"type": "delta", "text": delta_text}
                yield {
                    "type": "complete",
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
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
                if isinstance(parsed, dict):
                    _raise_payload_error_if_present(
                        parsed,
                        provider_code_prefix=self._provider_code_prefix,
                    )
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
