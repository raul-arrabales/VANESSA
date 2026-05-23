import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ManagedModel } from "../../../api/modelops";
import type { PlatformCapability, PlatformDeploymentProfile, PlatformProvider } from "../../../api/platform";
import {
  capabilitiesFixture,
  deploymentsFixture,
  embeddingsModelsFixture,
  knowledgeBasesFixture,
  llmModelsFixture,
  providersFixture,
} from "../../../test/platformControlFixtures";
import {
  type DeploymentFormState,
} from "../deploymentEditor";
import { usePlatformDeploymentEditor } from "./usePlatformDeploymentEditor";

function translate(key: string, options: Record<string, unknown> = {}): string {
  if (key === "platformControl.feedback.bindingRequired") {
    return "Select one provider for each required capability.";
  }
  if (key === "platformControl.feedback.resourceRequired") {
    return `Bind at least one ${String(options.capability ?? "")} resource.`;
  }
  if (key === "platformControl.feedback.defaultResourceRequired") {
    return `Select a default ${String(options.capability ?? "")} resource.`;
  }
  if (key === "platformControl.feedback.resourceProviderMismatch") {
    return `${String(options.provider ?? "")} cannot serve ${String(options.resources ?? "")}.`;
  }
  return key;
}

function cloudModelProviders(): PlatformProvider[] {
  return providersFixture.map((provider) =>
    provider.capability === "llm_inference" || provider.capability === "embeddings"
      ? { ...provider, provider_origin: "cloud" as const }
      : provider,
  );
}

type HookHarnessProps = {
  mode: "create" | "edit";
  deployment?: PlatformDeploymentProfile | null;
  formToValidate?: DeploymentFormState;
  capabilities?: PlatformCapability[];
  providers?: PlatformProvider[];
  eligibleModelsByCapability?: Record<string, ManagedModel[]>;
};

function HookHarness({
  mode,
  deployment = null,
  formToValidate,
  capabilities = capabilitiesFixture,
  providers = cloudModelProviders(),
  eligibleModelsByCapability = {
    llm_inference: llmModelsFixture,
    embeddings: embeddingsModelsFixture,
  },
}: HookHarnessProps): JSX.Element {
  const editor = usePlatformDeploymentEditor({
    mode,
    capabilities,
    providers,
    eligibleModelsByCapability,
    knowledgeBases: knowledgeBasesFixture,
    deployment,
    t: translate as never,
  });
  const validationResult = formToValidate ? editor.validateAndBuildMutation(formToValidate) : null;

  return (
    <div>
      <span data-testid="required-count">{String(editor.requiredCapabilities.length)}</span>
      <span data-testid="capability-count">{String(editor.capabilities.length)}</span>
      <span data-testid="llm-providers">{String(editor.providersByCapability.llm_inference?.length ?? 0)}</span>
      <span data-testid="embeddings-models">{String(editor.modelResourcesByCapability.embeddings?.length ?? 0)}</span>
      <span data-testid="initial-form">{JSON.stringify(editor.buildInitialForm())}</span>
      <span data-testid="initial-clone">{JSON.stringify(editor.buildInitialCloneForm())}</span>
      <span data-testid="validation-error">{validationResult?.validationError ?? ""}</span>
      <span data-testid="mutation-input">{JSON.stringify(validationResult?.mutationInput ?? null)}</span>
    </div>
  );
}

describe("usePlatformDeploymentEditor", () => {
  it("derives shared editor data and builds the same create-mode mutation payload", () => {
    const formToValidate: DeploymentFormState = {
      slug: "cloud-profile",
      displayName: "Cloud Profile",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
      },
      resourceIdsByCapability: {
        llm_inference: ["gpt-5", "gpt-4.1"],
        embeddings: ["text-embedding-3-small"],
        vector_store: ["kb_primary"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "gpt-4.1",
        embeddings: "text-embedding-3-small",
      },
      resourcePolicyByCapability: {
        vector_store: {
          selection_mode: "explicit",
        },
      },
    };

    render(<HookHarness mode="create" formToValidate={formToValidate} />);

    expect(screen.getByTestId("required-count")).toHaveTextContent("3");
    expect(screen.getByTestId("capability-count")).toHaveTextContent("3");
    expect(screen.getByTestId("llm-providers")).toHaveTextContent("1");
    expect(screen.getByTestId("embeddings-models")).toHaveTextContent("1");
    expect(screen.getByTestId("initial-form")).toHaveTextContent('"capabilityKeys":["llm_inference","embeddings","vector_store"]');
    expect(screen.getByTestId("initial-form")).toHaveTextContent('"slug":""');
    expect(screen.getByTestId("initial-clone")).toHaveTextContent("null");
    expect(screen.getByTestId("validation-error")).toHaveTextContent("");

    const mutationInput = JSON.parse(screen.getByTestId("mutation-input").textContent ?? "null") as {
      bindings: Array<{ capability: string; default_resource_id: string | null; resources: Array<{ id: string; resource_kind: string }> }>;
    };
    expect(mutationInput.bindings).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          capability: "llm_inference",
          default_resource_id: "gpt-4.1",
          resources: expect.arrayContaining([
            expect.objectContaining({ id: "gpt-5", resource_kind: "model" }),
            expect.objectContaining({ id: "gpt-4.1", resource_kind: "model" }),
          ]),
        }),
        expect.objectContaining({
          capability: "embeddings",
          default_resource_id: "text-embedding-3-small",
          resources: expect.arrayContaining([
            expect.objectContaining({ id: "text-embedding-3-small", resource_kind: "model" }),
          ]),
        }),
        expect.objectContaining({
              capability: "vector_store",
              default_resource_id: null,
              resources: expect.arrayContaining([
                expect.objectContaining({ id: "kb_primary", resource_kind: "knowledge_base", ref_type: "knowledge_base" }),
              ]),
            }),
      ]),
    );
  });

  it("builds initial edit-mode forms and returns the same validation failures", () => {
    const formToValidate: DeploymentFormState = {
      slug: "local-default",
      displayName: "Local Default",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
      },
      resourceIdsByCapability: {
        llm_inference: ["gpt-5"],
        embeddings: ["text-embedding-3-small"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "gpt-5",
      },
      resourcePolicyByCapability: {},
    };

    render(
      <HookHarness
        mode="edit"
        deployment={deploymentsFixture[0]}
        formToValidate={formToValidate}
      />,
    );

    expect(screen.getByTestId("initial-form")).toHaveTextContent('"slug":"local-default"');
    expect(screen.getByTestId("initial-clone")).toHaveTextContent('"slug":"local-default-copy"');
    expect(screen.getByTestId("validation-error")).toHaveTextContent("Select a default Embeddings resource.");
    expect(screen.getByTestId("mutation-input")).toHaveTextContent("null");
  });

  it("rejects model resources that do not match the selected provider origin", () => {
    const localLlmModel: ManagedModel = {
      ...llmModelsFixture[0],
      id: "qwen-local",
      name: "Qwen local",
      backend: "local",
      hosting: "local",
      availability: "offline_ready",
    };
    const formToValidate: DeploymentFormState = {
      slug: "cloud-profile",
      displayName: "Cloud Profile",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
      },
      resourceIdsByCapability: {
        llm_inference: ["qwen-local"],
        embeddings: ["text-embedding-3-small"],
        vector_store: ["kb_primary"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "qwen-local",
        embeddings: "text-embedding-3-small",
      },
      resourcePolicyByCapability: {
        vector_store: {
          selection_mode: "explicit",
        },
      },
    };

    render(
      <HookHarness
        mode="create"
        formToValidate={formToValidate}
        providers={cloudModelProviders()}
        eligibleModelsByCapability={{
          llm_inference: [localLlmModel],
          embeddings: embeddingsModelsFixture,
        }}
      />,
    );

    expect(screen.getByTestId("validation-error")).toHaveTextContent("vLLM local gateway cannot serve Qwen local.");
    expect(screen.getByTestId("mutation-input")).toHaveTextContent("null");
  });

  it("includes configured optional capabilities in the mutation payload without requiring blank optional rows", () => {
    const capabilitiesWithOptional = [
      ...capabilitiesFixture,
      {
        capability: "sandbox_execution",
        display_name: "Sandbox execution",
        description: "Sandbox capability",
        required: false,
        active_provider: null,
      },
    ];
    const providersWithOptional = [
      ...cloudModelProviders(),
      {
        ...providersFixture[0],
        id: "provider-sandbox",
        slug: "sandbox-local",
        provider_key: "sandbox_local",
        capability: "sandbox_execution",
        adapter_kind: "sandbox_http",
        provider_origin: "local" as const,
        display_name: "Sandbox local",
      },
    ];
    const formToValidate: DeploymentFormState = {
      slug: "cloud-profile",
      displayName: "Cloud Profile",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store", "sandbox_execution"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
        sandbox_execution: "provider-sandbox",
      },
      resourceIdsByCapability: {
        llm_inference: ["gpt-5"],
        embeddings: ["text-embedding-3-small"],
        vector_store: ["kb_primary"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "gpt-5",
        embeddings: "text-embedding-3-small",
      },
      resourcePolicyByCapability: {
        vector_store: {
          selection_mode: "explicit",
        },
      },
    };

    render(
      <HookHarness
        mode="create"
        capabilities={capabilitiesWithOptional}
        formToValidate={formToValidate}
        providers={providersWithOptional}
        eligibleModelsByCapability={{
          llm_inference: llmModelsFixture,
          embeddings: embeddingsModelsFixture,
        }}
      />,
    );

    const mutationInput = JSON.parse(screen.getByTestId("mutation-input").textContent ?? "null") as {
      bindings: Array<Record<string, unknown>>;
    };
    expect(mutationInput.bindings.map((binding) => binding.capability)).toEqual([
      "llm_inference",
      "embeddings",
      "vector_store",
      "sandbox_execution",
    ]);
    const sandboxBinding = mutationInput.bindings.find((binding) => binding.capability === "sandbox_execution");
    expect(sandboxBinding).toEqual(
      expect.objectContaining({ provider_id: "provider-sandbox", config: {} }),
    );
    expect(sandboxBinding).not.toHaveProperty("resources");
    expect(sandboxBinding).not.toHaveProperty("default_resource_id");
    expect(sandboxBinding).not.toHaveProperty("resource_policy");
  });

  it("serializes image-analysis resources with task defaults and no global default", () => {
    const imageModels: ManagedModel[] = [
      {
        ...llmModelsFixture[0],
        id: "plate-detector",
        name: "Plate detector",
        backend: "local",
        hosting: "local",
        task_key: "image_plate_detection",
      },
      {
        ...llmModelsFixture[0],
        id: "plate-ocr",
        name: "Plate OCR",
        backend: "local",
        hosting: "local",
        task_key: "image_plate_ocr",
      },
      {
        ...llmModelsFixture[0],
        id: "object-detector",
        name: "Object detector",
        backend: "local",
        hosting: "local",
        task_key: "object_detection",
      },
      {
        ...llmModelsFixture[0],
        id: "captioner",
        name: "Captioner",
        backend: "local",
        hosting: "local",
        task_key: "image_captioning",
      },
    ];
    const capabilitiesWithImage = [
      ...capabilitiesFixture,
      {
        capability: "image_analysis",
        display_name: "Image analysis",
        description: "Image capability",
        required: false,
        active_provider: null,
      },
    ];
    const providersWithImage = [
      ...cloudModelProviders(),
      {
        ...providersFixture[0],
        id: "provider-image",
        slug: "image-analysis-local",
        provider_key: "image_analysis_local",
        capability: "image_analysis",
        adapter_kind: "image_analysis_http",
        provider_origin: "local" as const,
        display_name: "Image analysis local",
      },
    ];
    const formToValidate: DeploymentFormState = {
      slug: "vision-profile",
      displayName: "Vision Profile",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store", "image_analysis"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
        image_analysis: "provider-image",
      },
      resourceIdsByCapability: {
        llm_inference: ["gpt-5"],
        embeddings: ["text-embedding-3-small"],
        vector_store: ["kb_primary"],
        image_analysis: ["plate-detector", "plate-ocr", "object-detector", "captioner"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "gpt-5",
        embeddings: "text-embedding-3-small",
        image_analysis: "ignored",
      },
      resourcePolicyByCapability: {
        vector_store: { selection_mode: "explicit" },
      },
    };

    render(
      <HookHarness
        mode="create"
        capabilities={capabilitiesWithImage}
        providers={providersWithImage}
        formToValidate={formToValidate}
        eligibleModelsByCapability={{
          llm_inference: llmModelsFixture,
          embeddings: embeddingsModelsFixture,
          image_analysis: imageModels,
        }}
      />,
    );

    expect(screen.getByTestId("validation-error")).toHaveTextContent("");
    const mutationInput = JSON.parse(screen.getByTestId("mutation-input").textContent ?? "null") as {
      bindings: Array<Record<string, unknown>>;
    };
    const imageBinding = mutationInput.bindings.find((binding) => binding.capability === "image_analysis");
    expect(imageBinding).toEqual(
      expect.objectContaining({
        provider_id: "provider-image",
        default_resource_id: null,
        resource_policy: {
          selection_mode: "task_defaults",
          task_defaults: {
            plate_detector: "plate-detector",
            plate_ocr: "plate-ocr",
            object_detector: "object-detector",
            captioner: "captioner",
          },
        },
      }),
    );
  });

  it("allows image-analysis bindings with only a complete captioning task group", () => {
    const imageModels: ManagedModel[] = [
      {
        ...llmModelsFixture[0],
        id: "captioner",
        name: "Captioner",
        backend: "local",
        hosting: "local",
        task_key: "image_captioning",
      },
    ];
    const capabilitiesWithImage = [
      ...capabilitiesFixture,
      {
        capability: "image_analysis",
        display_name: "Image analysis",
        description: "Image capability",
        required: false,
        active_provider: null,
      },
    ];
    const providersWithImage = [
      ...cloudModelProviders(),
      {
        ...providersFixture[0],
        id: "provider-image",
        slug: "image-analysis-local",
        provider_key: "image_analysis_local",
        capability: "image_analysis",
        adapter_kind: "image_analysis_http",
        provider_origin: "local" as const,
        display_name: "Image analysis local",
      },
    ];
    const formToValidate: DeploymentFormState = {
      slug: "vision-profile",
      displayName: "Vision Profile",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store", "image_analysis"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
        image_analysis: "provider-image",
      },
      resourceIdsByCapability: {
        llm_inference: ["gpt-5"],
        embeddings: ["text-embedding-3-small"],
        vector_store: ["kb_primary"],
        image_analysis: ["captioner"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "gpt-5",
        embeddings: "text-embedding-3-small",
      },
      resourcePolicyByCapability: {
        vector_store: { selection_mode: "explicit" },
      },
    };

    render(
      <HookHarness
        mode="create"
        capabilities={capabilitiesWithImage}
        providers={providersWithImage}
        formToValidate={formToValidate}
        eligibleModelsByCapability={{
          llm_inference: llmModelsFixture,
          embeddings: embeddingsModelsFixture,
          image_analysis: imageModels,
        }}
      />,
    );

    expect(screen.getByTestId("validation-error")).toHaveTextContent("");
    const mutationInput = JSON.parse(screen.getByTestId("mutation-input").textContent ?? "null") as {
      bindings: Array<Record<string, unknown>>;
    };
    const imageBinding = mutationInput.bindings.find((binding) => binding.capability === "image_analysis");
    expect(imageBinding).toEqual(
      expect.objectContaining({
        default_resource_id: null,
        resource_policy: {
          selection_mode: "task_defaults",
          task_defaults: {
            captioner: "captioner",
          },
        },
      }),
    );
  });

  it("rejects incomplete image-analysis ANPR task groups", () => {
    const imageModels: ManagedModel[] = [
      {
        ...llmModelsFixture[0],
        id: "plate-detector",
        name: "Plate detector",
        backend: "local",
        hosting: "local",
        task_key: "image_plate_detection",
      },
    ];
    const capabilitiesWithImage = [
      ...capabilitiesFixture,
      {
        capability: "image_analysis",
        display_name: "Image analysis",
        description: "Image capability",
        required: false,
        active_provider: null,
      },
    ];
    const providersWithImage = [
      ...cloudModelProviders(),
      {
        ...providersFixture[0],
        id: "provider-image",
        slug: "image-analysis-local",
        provider_key: "image_analysis_local",
        capability: "image_analysis",
        adapter_kind: "image_analysis_http",
        provider_origin: "local" as const,
        display_name: "Image analysis local",
      },
    ];
    const formToValidate: DeploymentFormState = {
      slug: "vision-profile",
      displayName: "Vision Profile",
      description: "",
      capabilityKeys: ["llm_inference", "embeddings", "vector_store", "image_analysis"],
      providerIdsByCapability: {
        llm_inference: "provider-1",
        embeddings: "provider-embeddings",
        vector_store: "provider-2",
        image_analysis: "provider-image",
      },
      resourceIdsByCapability: {
        llm_inference: ["gpt-5"],
        embeddings: ["text-embedding-3-small"],
        vector_store: ["kb_primary"],
        image_analysis: ["plate-detector"],
      },
      defaultResourceIdsByCapability: {
        llm_inference: "gpt-5",
        embeddings: "text-embedding-3-small",
      },
      resourcePolicyByCapability: {
        vector_store: { selection_mode: "explicit" },
      },
    };

    render(
      <HookHarness
        mode="create"
        capabilities={capabilitiesWithImage}
        providers={providersWithImage}
        formToValidate={formToValidate}
        eligibleModelsByCapability={{
          llm_inference: llmModelsFixture,
          embeddings: embeddingsModelsFixture,
          image_analysis: imageModels,
        }}
      />,
    );

    expect(screen.getByTestId("validation-error")).toHaveTextContent(
      "Image analysis requires at least one complete task resource group.",
    );
  });
});
