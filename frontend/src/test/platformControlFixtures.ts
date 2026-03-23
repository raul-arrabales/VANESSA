import { vi } from "vitest";
import type { ManagedModel } from "../api/modelops";
import type { PlatformDeploymentProfile } from "../api/platform";
import * as modelsApi from "../api/modelops";
import * as platformApi from "../api/platform";

export const capabilitiesFixture = [
  {
    capability: "llm_inference",
    display_name: "LLM inference",
    description: "Normalized chat and generation capability.",
    required: true,
    active_provider: {
      id: "provider-1",
      slug: "vllm-local-gateway",
      provider_key: "vllm_local",
      display_name: "vLLM local gateway",
      deployment_profile_id: "deployment-1",
      deployment_profile_slug: "local-default",
    },
  },
  {
    capability: "embeddings",
    display_name: "Embeddings",
    description: "Normalized text embeddings capability.",
    required: true,
    active_provider: {
      id: "provider-embeddings",
      slug: "vllm-embeddings-local",
      provider_key: "vllm_embeddings_local",
      display_name: "vLLM embeddings local",
      deployment_profile_id: "deployment-1",
      deployment_profile_slug: "local-default",
    },
  },
  {
    capability: "vector_store",
    display_name: "Vector store",
    description: "Semantic retrieval capability.",
    required: true,
    active_provider: {
      id: "provider-2",
      slug: "weaviate-local",
      provider_key: "weaviate_local",
      display_name: "Weaviate local",
      deployment_profile_id: "deployment-1",
      deployment_profile_slug: "local-default",
    },
  },
];

export const providerFamiliesFixture = [
  {
    provider_key: "vllm_local",
    capability: "llm_inference",
    adapter_kind: "openai_compatible_llm",
    display_name: "vLLM local gateway",
    description: "Local vLLM family.",
  },
  {
    provider_key: "vllm_embeddings_local",
    capability: "embeddings",
    adapter_kind: "openai_compatible_embeddings",
    display_name: "vLLM embeddings local",
    description: "Local embeddings family.",
  },
  {
    provider_key: "weaviate_local",
    capability: "vector_store",
    adapter_kind: "weaviate_http",
    display_name: "Weaviate local",
    description: "Local Weaviate family.",
  },
];

export const providersFixture = [
  {
    id: "provider-1",
    slug: "vllm-local-gateway",
    provider_key: "vllm_local",
    capability: "llm_inference",
    adapter_kind: "openai_compatible_llm",
    display_name: "vLLM local gateway",
    description: "Primary llm endpoint.",
    endpoint_url: "http://llm:8000",
    healthcheck_url: "http://llm:8000/health",
    enabled: true,
    config: {},
    secret_refs: {},
  },
  {
    id: "provider-embeddings",
    slug: "vllm-embeddings-local",
    provider_key: "vllm_embeddings_local",
    capability: "embeddings",
    adapter_kind: "openai_compatible_embeddings",
    display_name: "vLLM embeddings local",
    description: "Primary embeddings endpoint.",
    endpoint_url: "http://llm:8000",
    healthcheck_url: "http://llm:8000/health",
    enabled: true,
    config: {},
    secret_refs: {},
  },
  {
    id: "provider-2",
    slug: "weaviate-local",
    provider_key: "weaviate_local",
    capability: "vector_store",
    adapter_kind: "weaviate_http",
    display_name: "Weaviate local",
    description: "Primary vector endpoint.",
    endpoint_url: "http://weaviate:8080",
    healthcheck_url: "http://weaviate:8080/v1/.well-known/ready",
    enabled: true,
    config: {},
    secret_refs: {},
  },
];

export const llmModelsFixture: ManagedModel[] = [
  {
    id: "gpt-5",
    name: "GPT-5",
    provider: "openai",
    backend: "external_api",
    source: "external_provider",
    availability: "online_only",
    task_key: "llm",
    category: "generative",
    lifecycle_state: "active",
    is_validation_current: true,
    last_validation_status: "success",
  },
  {
    id: "gpt-4.1",
    name: "GPT-4.1",
    provider: "openai",
    backend: "external_api",
    source: "external_provider",
    availability: "online_only",
    task_key: "llm",
    category: "generative",
    lifecycle_state: "active",
    is_validation_current: true,
    last_validation_status: "success",
  },
];

export const embeddingsModelsFixture: ManagedModel[] = [
  {
    id: "text-embedding-3-small",
    name: "text-embedding-3-small",
    provider: "openai",
    backend: "external_api",
    source: "external_provider",
    availability: "online_only",
    task_key: "embeddings",
    category: "predictive",
    lifecycle_state: "active",
    is_validation_current: true,
    last_validation_status: "success",
  },
];

export const deploymentsFixture: PlatformDeploymentProfile[] = [
  {
    id: "deployment-1",
    slug: "local-default",
    display_name: "Local Default",
    description: "Default local profile.",
    is_active: true,
    bindings: [
      {
        capability: "llm_inference",
        provider: {
          id: "provider-1",
          slug: "vllm-local-gateway",
          provider_key: "vllm_local",
          display_name: "vLLM local gateway",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_llm",
        },
        served_models: [
          {
            id: "gpt-5",
            name: "GPT-5",
            task_key: "llm",
            backend: "external_api",
          },
          {
            id: "gpt-4.1",
            name: "GPT-4.1",
            task_key: "llm",
            backend: "external_api",
          },
        ],
        default_served_model_id: "gpt-5",
        default_served_model: {
          id: "gpt-5",
          name: "GPT-5",
          task_key: "llm",
          backend: "external_api",
        },
        config: {},
      },
      {
        capability: "embeddings",
        provider: {
          id: "provider-embeddings",
          slug: "vllm-embeddings-local",
          provider_key: "vllm_embeddings_local",
          display_name: "vLLM embeddings local",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_embeddings",
        },
        served_models: [
          {
            id: "text-embedding-3-small",
            name: "text-embedding-3-small",
            task_key: "embeddings",
            backend: "external_api",
          },
        ],
        default_served_model_id: "text-embedding-3-small",
        default_served_model: {
          id: "text-embedding-3-small",
          name: "text-embedding-3-small",
          task_key: "embeddings",
          backend: "external_api",
        },
        config: {},
      },
      {
        capability: "vector_store",
        provider: {
          id: "provider-2",
          slug: "weaviate-local",
          provider_key: "weaviate_local",
          display_name: "Weaviate local",
          endpoint_url: "http://weaviate:8080",
          enabled: true,
          adapter_kind: "weaviate_http",
        },
        served_models: [],
        default_served_model_id: null,
        default_served_model: null,
        config: {},
      },
    ],
  },
  {
    id: "deployment-2",
    slug: "staging-profile",
    display_name: "Staging Profile",
    description: "Alternate profile.",
    is_active: false,
    bindings: [
      {
        capability: "llm_inference",
        provider: {
          id: "provider-1",
          slug: "vllm-local-gateway",
          provider_key: "vllm_local",
          display_name: "vLLM local gateway",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_llm",
        },
        served_models: [
          {
            id: "gpt-5",
            name: "GPT-5",
            task_key: "llm",
            backend: "external_api",
          },
        ],
        default_served_model_id: "gpt-5",
        default_served_model: {
          id: "gpt-5",
          name: "GPT-5",
          task_key: "llm",
          backend: "external_api",
        },
        config: {},
      },
      {
        capability: "embeddings",
        provider: {
          id: "provider-embeddings",
          slug: "vllm-embeddings-local",
          provider_key: "vllm_embeddings_local",
          display_name: "vLLM embeddings local",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_embeddings",
        },
        served_models: [
          {
            id: "text-embedding-3-small",
            name: "text-embedding-3-small",
            task_key: "embeddings",
            backend: "external_api",
          },
        ],
        default_served_model_id: "text-embedding-3-small",
        default_served_model: {
          id: "text-embedding-3-small",
          name: "text-embedding-3-small",
          task_key: "embeddings",
          backend: "external_api",
        },
        config: {},
      },
      {
        capability: "vector_store",
        provider: {
          id: "provider-2",
          slug: "weaviate-local",
          provider_key: "weaviate_local",
          display_name: "Weaviate local",
          endpoint_url: "http://weaviate:8080",
          enabled: true,
          adapter_kind: "weaviate_http",
        },
        served_models: [],
        default_served_model_id: null,
        default_served_model: null,
        config: {},
      },
    ],
  },
];

export const activationAuditFixture = [
  {
    id: "audit-1",
    deployment_profile: {
      id: "deployment-1",
      slug: "local-default",
      display_name: "Local Default",
    },
    previous_deployment_profile: null,
    activated_by_user_id: 1,
    activated_at: "2026-01-01T00:00:00+00:00",
  },
];

export function primePlatformControlMocks(): void {
  vi.mocked(platformApi.listPlatformCapabilities).mockResolvedValue(capabilitiesFixture);
  vi.mocked(platformApi.listPlatformProviderFamilies).mockResolvedValue(providerFamiliesFixture);
  vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(providersFixture);
  vi.mocked(platformApi.listPlatformDeployments).mockResolvedValue(deploymentsFixture);
  vi.mocked(platformApi.listPlatformActivationAudit).mockResolvedValue(activationAuditFixture);
  vi.mocked(modelsApi.listModelOpsModels).mockImplementation(async (_token, options) => {
    if (options?.capability === "llm_inference") {
      return llmModelsFixture;
    }
    if (options?.capability === "embeddings") {
      return embeddingsModelsFixture;
    }
    return [...llmModelsFixture, ...embeddingsModelsFixture];
  });
}
