from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import LLMConfig
from app.providers.base import ProviderError
from app.providers.base import RoutedModelProvider


@dataclass(frozen=True)
class ModelCapabilities:
    text: bool
    image_input: bool
    embeddings: bool


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
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class EmbeddingResult:
    embeddings: list[list[float]]
    prompt_tokens: int = 0


@dataclass(frozen=True)
class ResolvedModel:
    model: ModelInfo
    provider: RoutedModelProvider


class ModelRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, RoutedModelProvider] = {}
        self._models: dict[str, ModelInfo] = {}
        self._aliases: dict[str, str] = {}
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
        self._aliases = {}

        self.register_provider(
            "local_vllm",
            LocalVLLMProvider(
                text_base_url=config.local_base_url,
                embeddings_base_url=config.local_embeddings_base_url,
                timeout_seconds=config.request_timeout_seconds,
            ),
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
                    capabilities=ModelCapabilities(text=True, image_input=False, embeddings=False),
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
                    capabilities=ModelCapabilities(text=True, image_input=False, embeddings=False),
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

    def _register_or_merge_model(self, model: ModelInfo) -> None:
        existing = self._models.get(model.id)
        if existing is None:
            self.register_model(model)
            return
        merged_metadata = {**existing.metadata, **model.metadata}
        self._models[model.id] = ModelInfo(
            id=existing.id,
            display_name=existing.display_name if existing.display_name == model.display_name else existing.display_name,
            capabilities=ModelCapabilities(
                text=existing.capabilities.text or model.capabilities.text,
                image_input=existing.capabilities.image_input or model.capabilities.image_input,
                embeddings=existing.capabilities.embeddings or model.capabilities.embeddings,
            ),
            status=existing.status,
            provider_type=existing.provider_type,
            provider_config_ref=existing.provider_config_ref,
            upstream_model=existing.upstream_model or model.upstream_model,
            metadata=merged_metadata,
        )

    def list_models(self) -> list[ModelInfo]:
        models = dict(self._models)
        models.update(self._local_runtime_models())
        return [models[model_id] for model_id in sorted(models.keys())]

    def resolve_model(self, model_id: str) -> ResolvedModel:
        runtime_models = self._local_runtime_models()
        runtime_aliases = self._local_runtime_aliases(runtime_models)
        resolved_model_id = runtime_aliases.get(self._aliases.get(model_id, model_id), self._aliases.get(model_id, model_id))
        models = {**self._models, **runtime_models}
        try:
            model = models[resolved_model_id]
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

    def _local_runtime_models(self) -> dict[str, ModelInfo]:
        provider = self._providers.get("local_vllm")
        if provider is None:
            return {}
        had_error = False
        text_items: list[dict[str, object]] = []
        embeddings_items: list[dict[str, object]] = []
        try:
            text_items = provider.list_models(capability="llm_inference")
        except ProviderError:
            had_error = True
        try:
            embeddings_items = provider.list_models(capability="embeddings")
        except ProviderError:
            had_error = True
        if not text_items and not embeddings_items and had_error:
            return self._fallback_local_models()
        models: dict[str, ModelInfo] = {}
        for item in text_items:
            info = self._model_from_runtime_item(item, capability="llm_inference")
            if info is not None:
                models[info.id] = info
        for item in embeddings_items:
            info = self._model_from_runtime_item(item, capability="embeddings")
            if info is None:
                continue
            existing = models.get(info.id)
            if existing is None:
                models[info.id] = info
                continue
            models[info.id] = ModelInfo(
                id=existing.id,
                display_name=existing.display_name,
                capabilities=ModelCapabilities(
                    text=existing.capabilities.text or info.capabilities.text,
                    image_input=existing.capabilities.image_input or info.capabilities.image_input,
                    embeddings=existing.capabilities.embeddings or info.capabilities.embeddings,
                ),
                status=existing.status,
                provider_type=existing.provider_type,
                provider_config_ref=existing.provider_config_ref,
                upstream_model=existing.upstream_model or info.upstream_model,
                metadata={**existing.metadata, **info.metadata},
            )
        return models

    def _local_runtime_aliases(self, models: dict[str, ModelInfo]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        text_candidates = [model.id for model in models.values() if model.capabilities.text]
        embeddings_candidates = [model.id for model in models.values() if model.capabilities.embeddings]
        if text_candidates:
            aliases["local-vllm-default"] = sorted(text_candidates)[0]
        if embeddings_candidates:
            aliases["local-vllm-embeddings-default"] = sorted(embeddings_candidates)[0]
        return aliases

    def _model_from_runtime_item(self, item: dict[str, object], *, capability: str) -> ModelInfo | None:
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            return None
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        capabilities = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
        display_name = str(item.get("display_name") or model_id).strip() or model_id
        return ModelInfo(
            id=model_id,
            display_name=display_name,
            capabilities=ModelCapabilities(
                text=bool(capabilities.get("text")) if capability == "llm_inference" else False,
                image_input=bool(capabilities.get("image_input")) if capability == "llm_inference" else False,
                embeddings=bool(capabilities.get("embeddings")) if capability == "embeddings" else False,
            ),
            status=str(item.get("status") or "available").strip() or "available",
            provider_type="local_vllm",
            provider_config_ref="local/default" if capability == "llm_inference" else "local/embeddings",
            upstream_model=str(metadata.get("upstream_model") or model_id).strip() or model_id,
            metadata=dict(metadata),
        )

    def _fallback_local_models(self) -> dict[str, ModelInfo]:
        config = self.config
        models: dict[str, ModelInfo] = {
            config.local_upstream_model: ModelInfo(
                id=config.local_upstream_model,
                display_name="Local vLLM Default",
                capabilities=ModelCapabilities(text=True, image_input=False, embeddings=False),
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
        }
        embeddings = ModelInfo(
            id=config.local_embeddings_upstream_model,
            display_name="Local vLLM Embeddings Default",
            capabilities=ModelCapabilities(text=False, image_input=False, embeddings=True),
            status="available",
            provider_type="local_vllm",
            provider_config_ref="local/embeddings",
            upstream_model=config.local_embeddings_upstream_model,
            metadata={"upstream_model": config.local_embeddings_upstream_model, "supports_embeddings": True},
        )
        existing = models.get(embeddings.id)
        if existing is None:
            models[embeddings.id] = embeddings
        else:
            models[embeddings.id] = ModelInfo(
                id=existing.id,
                display_name=existing.display_name,
                capabilities=ModelCapabilities(text=True, image_input=False, embeddings=True),
                status=existing.status,
                provider_type=existing.provider_type,
                provider_config_ref=existing.provider_config_ref,
                upstream_model=existing.upstream_model,
                metadata={**existing.metadata, **embeddings.metadata},
            )
        return models


registry = ModelRegistry()
