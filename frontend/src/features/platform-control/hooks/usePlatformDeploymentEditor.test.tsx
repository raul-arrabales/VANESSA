import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PlatformDeploymentProfile } from "../../../api/platform";
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
  return key;
}

type HookHarnessProps = {
  mode: "create" | "edit";
  deployment?: PlatformDeploymentProfile | null;
  formToValidate?: DeploymentFormState;
};

function HookHarness({
  mode,
  deployment = null,
  formToValidate,
}: HookHarnessProps): JSX.Element {
  const editor = usePlatformDeploymentEditor({
    mode,
    capabilities: capabilitiesFixture,
    providers: providersFixture,
    eligibleModelsByCapability: {
      llm_inference: llmModelsFixture,
      embeddings: embeddingsModelsFixture,
    },
    knowledgeBases: knowledgeBasesFixture,
    deployment,
    t: translate as never,
  });
  const validationResult = formToValidate ? editor.validateAndBuildMutation(formToValidate) : null;

  return (
    <div>
      <span data-testid="required-count">{String(editor.requiredCapabilities.length)}</span>
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
    expect(screen.getByTestId("llm-providers")).toHaveTextContent("1");
    expect(screen.getByTestId("embeddings-models")).toHaveTextContent("1");
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
});
