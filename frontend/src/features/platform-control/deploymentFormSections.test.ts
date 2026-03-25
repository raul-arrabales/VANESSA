import { describe, expect, it } from "vitest";
import type { ManagedModel } from "../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../api/platform";
import {
  buildDeploymentCapabilitySectionState,
} from "./deploymentFormSections";
import type { DeploymentFormState } from "./utils";

function translate(key: string, options: Record<string, unknown> = {}): string {
  if (key === "platformControl.summary.none") {
    return "None";
  }
  if (key === "platformControl.forms.deployment.loadedModelNotEligibleHint") {
    return `${String(options.provider ?? "")} currently has ${String(options.model ?? "")} loaded, but deployment bindings only allow ModelOps-eligible ${String(options.capability ?? "")} models.`;
  }
  if (key === "platformControl.forms.deployment.noEligibleResourcesHint") {
    return `No ModelOps-eligible ${String(options.capability ?? "")} resources are currently available for binding.`;
  }
  return key;
}

function buildCapability(overrides: Partial<PlatformCapability> = {}): PlatformCapability {
  return {
    capability: "llm_inference",
    display_name: "LLM inference",
    description: "LLM capability",
    required: true,
    active_provider: null,
    ...overrides,
  };
}

function buildProvider(overrides: Partial<PlatformProvider> = {}): PlatformProvider {
  return {
    id: "provider-1",
    slug: "provider-1",
    provider_key: "vllm_local",
    capability: "llm_inference",
    adapter_kind: "openai_compatible_llm",
    display_name: "vLLM local gateway",
    description: "Primary llm provider",
    endpoint_url: "http://llm:8000",
    healthcheck_url: "http://llm:8000/health",
    enabled: true,
    config: {},
    secret_refs: {},
    ...overrides,
  };
}

function buildModel(overrides: Partial<ManagedModel> = {}): ManagedModel {
  return {
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
    ...overrides,
  };
}

function buildFormState(overrides: Partial<DeploymentFormState> = {}): DeploymentFormState {
  return {
    slug: "local-default",
    displayName: "Local Default",
    description: "",
    providerIdsByCapability: {},
    resourceIdsByCapability: {},
    defaultResourceIdsByCapability: {},
    resourcePolicyByCapability: {},
    ...overrides,
  };
}

describe("buildDeploymentCapabilitySectionState", () => {
  it("builds model capability state with eligible resources and filtered default options", () => {
    const capability = buildCapability();
    const state = buildDeploymentCapabilitySectionState({
      capability,
      value: buildFormState({
        providerIdsByCapability: { llm_inference: "provider-1" },
        resourceIdsByCapability: { llm_inference: ["gpt-5"] },
        defaultResourceIdsByCapability: { llm_inference: "gpt-5" },
      }),
      providersByCapability: { llm_inference: [buildProvider()] },
      modelResourcesByCapability: {
        llm_inference: [buildModel(), buildModel({ id: "gpt-4.1", name: "GPT-4.1" })],
      },
      t: translate,
    });

    expect(state.capabilityMode).toBe("model");
    expect(state.selectedProvider?.id).toBe("provider-1");
    expect(state.availableDefaultResources.map((model) => model.id)).toEqual(["gpt-5"]);
    expect(state.loadedModelEligibilityHint).toBeNull();
    expect(state.noEligibleResourcesHint).toBeNull();
  });

  it("builds a loaded-but-ineligible hint when the selected provider has a loaded model but no eligible resources", () => {
    const capability = buildCapability({ capability: "embeddings", display_name: "Embeddings" });
    const state = buildDeploymentCapabilitySectionState({
      capability,
      value: buildFormState({
        providerIdsByCapability: { embeddings: "provider-embeddings" },
      }),
      providersByCapability: {
        embeddings: [
          buildProvider({
            id: "provider-embeddings",
            capability: "embeddings",
            provider_key: "vllm_embeddings_local",
            display_name: "vLLM embeddings local",
            loaded_managed_model_id: "sentence-transformers--all-MiniLM-L6-v2",
            loaded_managed_model_name: "all-MiniLM-L6-v2",
          }),
        ],
      },
      modelResourcesByCapability: { embeddings: [] },
      t: translate,
    });

    expect(state.loadedModelEligibilityHint).toContain("vLLM embeddings local currently has all-MiniLM-L6-v2 loaded");
    expect(state.noEligibleResourcesHint).toBeNull();
  });

  it("builds a generic empty-state hint when no eligible model resources are available", () => {
    const capability = buildCapability({ capability: "embeddings", display_name: "Embeddings" });
    const state = buildDeploymentCapabilitySectionState({
      capability,
      value: buildFormState({
        providerIdsByCapability: { embeddings: "provider-embeddings" },
      }),
      providersByCapability: {
        embeddings: [
          buildProvider({
            id: "provider-embeddings",
            capability: "embeddings",
            provider_key: "vllm_embeddings_local",
            display_name: "vLLM embeddings local",
          }),
        ],
      },
      modelResourcesByCapability: { embeddings: [] },
      t: translate,
    });

    expect(state.loadedModelEligibilityHint).toBeNull();
    expect(state.noEligibleResourcesHint).toBe("No ModelOps-eligible Embeddings resources are currently available for binding.");
  });

  it("builds vector capability state for explicit and dynamic namespace modes", () => {
    const capability = buildCapability({ capability: "vector_store", display_name: "Vector store" });
    const explicitState = buildDeploymentCapabilitySectionState({
      capability,
      value: buildFormState({
        resourceIdsByCapability: { vector_store: ["kb_primary"] },
      }),
      providersByCapability: { vector_store: [buildProvider({ id: "provider-2", capability: "vector_store" })] },
      modelResourcesByCapability: {},
      t: translate,
    });
    const dynamicState = buildDeploymentCapabilitySectionState({
      capability,
      value: buildFormState({
        resourcePolicyByCapability: {
          vector_store: {
            selection_mode: "dynamic_namespace",
            namespace_prefix: "kb_",
          },
        },
      }),
      providersByCapability: { vector_store: [buildProvider({ id: "provider-2", capability: "vector_store" })] },
      modelResourcesByCapability: {},
      t: translate,
    });

    expect(explicitState.capabilityMode).toBe("vector");
    expect(explicitState.vectorSelectionMode).toBe("explicit");
    expect(explicitState.selectedResourceIds).toEqual(["kb_primary"]);
    expect(dynamicState.vectorSelectionMode).toBe("dynamic_namespace");
    expect(dynamicState.namespacePrefix).toBe("kb_");
  });
});
