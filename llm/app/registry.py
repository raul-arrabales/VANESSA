from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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


class ModelProvider(Protocol):
    @property
    def info(self) -> ModelInfo:
        """Metadata describing the provider's model."""


@dataclass(frozen=True)
class DummyModelProvider:
    info: ModelInfo


class ModelRegistry:
    def __init__(self, providers: list[ModelProvider] | None = None) -> None:
        self._providers: dict[str, ModelProvider] = {}
        for provider in providers or []:
            self._providers[provider.info.id] = provider

    def list_models(self) -> list[ModelInfo]:
        return [provider.info for provider in self._providers.values()]

    def get_model(self, model_id: str) -> ModelProvider:
        try:
            return self._providers[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model: {model_id}") from exc


registry = ModelRegistry(
    providers=[
        DummyModelProvider(
            info=ModelInfo(
                id="dummy",
                display_name="Dummy Test Model",
                capabilities=ModelCapabilities(text=True, image_input=False),
                status="available",
                provider_type="dummy",
            )
        )
    ]
)
