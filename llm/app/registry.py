from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import ResponseRequest


@dataclass(frozen=True)
class ModelCapabilities:
    text: bool
    image_input: bool


@dataclass(frozen=True)
class ModelInfo:
    id: str
    display_name: str
    capabilities: ModelCapabilities
    status: str
    provider_type: str


@dataclass(frozen=True)
class ProviderResult:
    output_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ModelProvider(Protocol):
    @property
    def info(self) -> ModelInfo:
        """Metadata describing the provider's model."""

    def generate(self, request: ResponseRequest) -> ProviderResult:
        """Generates a response from the incoming request."""


class ModelRegistry:
    def __init__(self, providers: list[ModelProvider] | None = None) -> None:
        self._providers: dict[str, ModelProvider] = {}
        for provider in providers or []:
            self.register_provider(provider)

    def register_provider(self, provider: ModelProvider) -> None:
        self._providers[provider.info.id] = provider

    def list_models(self) -> list[ModelInfo]:
        return [provider.info for provider in self._providers.values()]

    def get_model(self, model_id: str) -> ModelProvider:
        try:
            return self._providers[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model: {model_id}") from exc


registry = ModelRegistry()
