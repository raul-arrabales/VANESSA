from __future__ import annotations

from app.registry import EmbeddingResult, ProviderResult
from app.schemas import EmbeddingRequest, ResponseRequest

from .base import ProviderError
from .openai_compat import OpenAICompatibleProvider


class OpenAIProvider:
    def __init__(self, *, base_url: str, timeout_seconds: int, api_key: str) -> None:
        self._api_key = api_key.strip()
        self._provider = OpenAICompatibleProvider(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            auth_header_value=f"Bearer {self._api_key}" if self._api_key else None,
            provider_code_prefix="openai",
        )

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        if not self._api_key:
            raise ProviderError(
                status_code=401,
                code="openai_auth_error",
                message="OPENAI_API_KEY is required for OpenAI inference.",
            )
        return self._provider.generate(request, upstream_model=upstream_model)

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> EmbeddingResult:
        if not self._api_key:
            raise ProviderError(
                status_code=401,
                code="openai_auth_error",
                message="OPENAI_API_KEY is required for OpenAI inference.",
            )
        return self._provider.embed(request, upstream_model=upstream_model)
