from __future__ import annotations

from app.registry import EmbeddingResult, ProviderResult
from app.schemas import EmbeddingRequest, ResponseRequest

from .base import ProviderError
from .openai_compat import OpenAICompatibleProvider


class HuggingFaceRouterProvider:
    def __init__(self, *, base_url: str, timeout_seconds: int, token: str) -> None:
        self._token = token.strip()
        self._provider = OpenAICompatibleProvider(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            auth_header_value=f"Bearer {self._token}" if self._token else None,
            provider_code_prefix="hf_router",
        )

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        if not self._token:
            raise ProviderError(
                status_code=401,
                code="hf_router_auth_error",
                message="HF_TOKEN is required for Hugging Face router inference.",
            )
        return self._provider.generate(request, upstream_model=upstream_model)

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> EmbeddingResult:
        if not self._token:
            raise ProviderError(
                status_code=401,
                code="hf_router_auth_error",
                message="HF_TOKEN is required for Hugging Face router inference.",
            )
        return self._provider.embed(request, upstream_model=upstream_model)
