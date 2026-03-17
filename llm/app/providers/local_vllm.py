from __future__ import annotations

from app.registry import EmbeddingResult, ProviderResult
from app.schemas import EmbeddingRequest, ResponseRequest

from .openai_compat import OpenAICompatibleProvider


class LocalVLLMProvider:
    def __init__(self, *, base_url: str, timeout_seconds: int) -> None:
        self._provider = OpenAICompatibleProvider(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            auth_header_value=None,
            provider_code_prefix="local_vllm",
        )

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        return self._provider.generate(request, upstream_model=upstream_model)

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> EmbeddingResult:
        return self._provider.embed(request, upstream_model=upstream_model)
