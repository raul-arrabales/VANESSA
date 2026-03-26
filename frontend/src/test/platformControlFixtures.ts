import { vi } from "vitest";
import type { KnowledgeBase } from "../api/context";
import type { ManagedModel } from "../api/modelops";
import type { PlatformDeploymentProfile } from "../api/platform";
import * as contextApi from "../api/context";
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

export const knowledgeBasesFixture: KnowledgeBase[] = [
  {
    id: "kb_primary",
    slug: "product-docs",
    display_name: "Product Docs",
    description: "Primary product documentation knowledge base.",
    index_name: "kb_product_docs",
    backing_provider_key: "weaviate_local",
    lifecycle_state: "active",
    sync_status: "ready",
    schema: {},
    document_count: 12,
    binding_count: 1,
  },
  {
    id: "kb_support",
    slug: "support-notes",
    display_name: "Support Notes",
    description: "Support issue and troubleshooting notes.",
    index_name: "kb_support_notes",
    backing_provider_key: "weaviate_local",
    lifecycle_state: "active",
    sync_status: "ready",
    schema: {},
    document_count: 4,
    binding_count: 0,
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
        resources: [
          {
            id: "gpt-5",
            resource_kind: "model",
            ref_type: "managed_model",
            managed_model_id: "gpt-5",
            provider_resource_id: "gpt-5",
            display_name: "GPT-5",
            metadata: { name: "GPT-5", task_key: "llm", backend: "external_api" },
          },
          {
            id: "gpt-4.1",
            resource_kind: "model",
            ref_type: "managed_model",
            managed_model_id: "gpt-4.1",
            provider_resource_id: "gpt-4.1",
            display_name: "GPT-4.1",
            metadata: { name: "GPT-4.1", task_key: "llm", backend: "external_api" },
          },
        ],
        default_resource_id: "gpt-5",
        default_resource: {
          id: "gpt-5",
          resource_kind: "model",
          ref_type: "managed_model",
          managed_model_id: "gpt-5",
          provider_resource_id: "gpt-5",
          display_name: "GPT-5",
          metadata: { name: "GPT-5", task_key: "llm", backend: "external_api" },
        },
        resource_policy: {},
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
        resources: [
          {
            id: "text-embedding-3-small",
            resource_kind: "model",
            ref_type: "managed_model",
            managed_model_id: "text-embedding-3-small",
            provider_resource_id: "text-embedding-3-small",
            display_name: "text-embedding-3-small",
            metadata: { name: "text-embedding-3-small", task_key: "embeddings", backend: "external_api" },
          },
        ],
        default_resource_id: "text-embedding-3-small",
        default_resource: {
          id: "text-embedding-3-small",
          resource_kind: "model",
          ref_type: "managed_model",
          managed_model_id: "text-embedding-3-small",
          provider_resource_id: "text-embedding-3-small",
          display_name: "text-embedding-3-small",
          metadata: { name: "text-embedding-3-small", task_key: "embeddings", backend: "external_api" },
        },
        resource_policy: {},
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
        resources: [],
        default_resource_id: null,
        default_resource: null,
        resource_policy: { selection_mode: "dynamic_namespace", namespace_prefix: "kb_" },
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
        resources: [
          {
            id: "gpt-5",
            resource_kind: "model",
            ref_type: "managed_model",
            managed_model_id: "gpt-5",
            provider_resource_id: "gpt-5",
            display_name: "GPT-5",
            metadata: { name: "GPT-5", task_key: "llm", backend: "external_api" },
          },
        ],
        default_resource_id: "gpt-5",
        default_resource: {
          id: "gpt-5",
          resource_kind: "model",
          ref_type: "managed_model",
          managed_model_id: "gpt-5",
          provider_resource_id: "gpt-5",
          display_name: "GPT-5",
          metadata: { name: "GPT-5", task_key: "llm", backend: "external_api" },
        },
        resource_policy: {},
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
        resources: [
          {
            id: "text-embedding-3-small",
            resource_kind: "model",
            ref_type: "managed_model",
            managed_model_id: "text-embedding-3-small",
            provider_resource_id: "text-embedding-3-small",
            display_name: "text-embedding-3-small",
            metadata: { name: "text-embedding-3-small", task_key: "embeddings", backend: "external_api" },
          },
        ],
        default_resource_id: "text-embedding-3-small",
        default_resource: {
          id: "text-embedding-3-small",
          resource_kind: "model",
          ref_type: "managed_model",
          managed_model_id: "text-embedding-3-small",
          provider_resource_id: "text-embedding-3-small",
          display_name: "text-embedding-3-small",
          metadata: { name: "text-embedding-3-small", task_key: "embeddings", backend: "external_api" },
        },
        resource_policy: {},
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
        resources: [],
        default_resource_id: null,
        default_resource: null,
        resource_policy: { selection_mode: "dynamic_namespace", namespace_prefix: "kb_" },
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
  vi.mocked(contextApi.listKnowledgeBases).mockResolvedValue(knowledgeBasesFixture);
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
