from __future__ import annotations

from dataclasses import dataclass

from app.registry import EmbeddingResult, ModelCapabilities, ModelInfo, ProviderResult
from app.schemas import EmbeddingRequest, ResponseRequest
from .base import ProviderError


@dataclass(frozen=True)
class DummyModelProvider:
    info: ModelInfo = ModelInfo(
        id="dummy",
        display_name="Dummy Test Model",
        capabilities=ModelCapabilities(text=True, image_input=False, embeddings=False),
        status="available",
        provider_type="dummy",
        provider_config_ref="dummy/default",
        upstream_model="dummy",
        metadata={
            "upstream_model": "dummy",
            "supports_image_input": False,
            "max_tokens_default": 128,
        },
    )

    def generate(self, request: ResponseRequest, *, upstream_model: str) -> ProviderResult:
        _ = request
        _ = upstream_model
        return ProviderResult(
            output_text="Hello, this is the test dummy model.",
            prompt_tokens=8,
            completion_tokens=8,
        )

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> EmbeddingResult:
        _ = (request, upstream_model)
        raise ProviderError(
            status_code=422,
            code="dummy_embeddings_unsupported",
            message="Dummy model does not support embeddings.",
        )
