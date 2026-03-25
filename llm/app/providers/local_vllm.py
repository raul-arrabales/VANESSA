from __future__ import annotations

from collections.abc import Iterator
from json import loads
from socket import timeout as socket_timeout
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.registry import EmbeddingResult, ProviderResult
from app.schemas import EmbeddingRequest, ResponseRequest

from .base import ProviderError
from .openai_compat import OpenAICompatibleProvider


class LocalVLLMProvider:
    def __init__(self, *, text_base_url: str, embeddings_base_url: str, timeout_seconds: int) -> None:
        self._text_provider = OpenAICompatibleProvider(
            base_url=text_base_url,
            timeout_seconds=timeout_seconds,
            auth_header_value=None,
            provider_code_prefix="local_vllm",
        )
        self._embeddings_provider = OpenAICompatibleProvider(
            base_url=embeddings_base_url,
            timeout_seconds=timeout_seconds,
            auth_header_value=None,
            provider_code_prefix="local_vllm",
        )
        self._timeout_seconds = timeout_seconds

    def list_models(self, *, capability: str) -> list[dict[str, object]]:
        if capability == "embeddings":
            return self._list_models_from_base(self._embeddings_provider.base_url)
        return self._list_models_from_base(self._text_provider.base_url)

    def _list_models_from_base(self, base_url: str) -> list[dict[str, object]]:
        request = Request(
            base_url.rstrip("/") + "/models",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = loads(response.read().decode("utf-8") or "{}")
        except TimeoutError as exc:
            raise ProviderError(status_code=504, code="local_vllm_unavailable", message="Local runtime timed out.") from exc
        except socket_timeout as exc:
            raise ProviderError(status_code=504, code="local_vllm_unavailable", message="Local runtime timed out.") from exc
        except HTTPError as exc:
            raise ProviderError(status_code=int(exc.code), code="local_vllm_unavailable", message="Local runtime failed.") from exc
        except URLError as exc:
            raise ProviderError(status_code=502, code="local_vllm_unavailable", message="Local runtime unavailable.") from exc
        data = payload.get("data")
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        return self._text_provider.generate(request, upstream_model=upstream_model)

    def generate_stream(
        self,
        request: ResponseRequest,
        *,
        upstream_model: str,
    ) -> Iterator[dict[str, object]]:
        return self._text_provider.generate_stream(request, upstream_model=upstream_model)

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> EmbeddingResult:
        return self._embeddings_provider.embed(request, upstream_model=upstream_model)
