from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import LLMConfig
from app.providers.base import RoutedModelProvider


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
    provider_config_ref: str | None = None
    upstream_model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResult:
    output_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class ResolvedModel:
    model: ModelInfo
    provider: RoutedModelProvider


class ModelRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, RoutedModelProvider] = {}
        self._models: dict[str, ModelInfo] = {}
        self._config: LLMConfig | None = None

    @property
    def config(self) -> LLMConfig:
        if self._config is None:
            raise RuntimeError("Model registry not configured.")
        return self._config

    def configure(self, config: LLMConfig) -> None:
        from app.providers.dummy import DummyModelProvider
        from app.providers.hf_router import HuggingFaceRouterProvider
        from app.providers.local_vllm import LocalVLLMProvider
        from app.providers.openai_provider import OpenAIProvider

        self._config = config
        self._providers = {}
        self._models = {}

        self.register_provider(
            "local_vllm",
            LocalVLLMProvider(
                base_url=config.local_base_url,
                timeout_seconds=config.request_timeout_seconds,
            ),
        )

        self.register_model(
            ModelInfo(
                id="local-vllm-default",
                display_name="Local vLLM Default",
                capabilities=ModelCapabilities(text=True, image_input=False),
                status="available",
                provider_type="local_vllm",
                provider_config_ref="local/default",
                upstream_model=config.local_upstream_model,
                metadata={
                    "upstream_model": config.local_upstream_model,
                    "supports_image_input": False,
                    "max_tokens_default": 512,
                },
            )
        )

        if config.enable_hf_router:
            self.register_provider(
                "hf_router",
                HuggingFaceRouterProvider(
                    base_url=config.hf_base_url,
                    timeout_seconds=config.request_timeout_seconds,
                    token=config.hf_token,
                ),
            )
            self.register_model(
                ModelInfo(
                    id="hf-router-default",
                    display_name="Hugging Face Router Default",
                    capabilities=ModelCapabilities(text=True, image_input=False),
                    status="available",
                    provider_type="hf_router",
                    provider_config_ref="hf_router/default",
                    upstream_model=config.hf_upstream_model,
                    metadata={
                        "upstream_model": config.hf_upstream_model,
                        "supports_image_input": False,
                        "max_tokens_default": 512,
                    },
                )
            )

        if config.enable_openai:
            self.register_provider(
                "openai",
                OpenAIProvider(
                    base_url=config.openai_base_url,
                    timeout_seconds=config.request_timeout_seconds,
                    api_key=config.openai_api_key,
                ),
            )
            self.register_model(
                ModelInfo(
                    id="openai-default",
                    display_name="OpenAI Default",
                    capabilities=ModelCapabilities(text=True, image_input=False),
                    status="available",
                    provider_type="openai",
                    provider_config_ref="openai/default",
                    upstream_model=config.openai_upstream_model,
                    metadata={
                        "upstream_model": config.openai_upstream_model,
                        "supports_image_input": False,
                        "max_tokens_default": 512,
                    },
                )
            )

        if config.enable_dummy_model:
            self.register_provider("dummy", DummyModelProvider())
            self.register_model(DummyModelProvider().info)

    def register_provider(self, name: str, provider: RoutedModelProvider) -> None:
        self._providers[name] = provider

    def register_model(self, model: ModelInfo) -> None:
        self._models[model.id] = model

    def list_models(self) -> list[ModelInfo]:
        return [self._models[model_id] for model_id in sorted(self._models.keys())]

    def resolve_model(self, model_id: str) -> ResolvedModel:
        try:
            model = self._models[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model: {model_id}") from exc

        provider = self._providers.get(model.provider_type)
        if provider is None:
            raise KeyError(f"No provider registered for model '{model_id}'")
        return ResolvedModel(model=model, provider=provider)

    def failover_models(self, requested_model: str) -> list[ResolvedModel]:
        config = self.config
        if not (config.routing_mode == "hybrid" and config.enable_cloud_failover):
            return []

        ordered_failovers = ["hf-router-default", "openai-default"]
        candidates: list[ResolvedModel] = []
        for model_id in ordered_failovers:
            if model_id == requested_model:
                continue
            if model_id in self._models:
                candidates.append(self.resolve_model(model_id))
        return candidates


registry = ModelRegistry()
