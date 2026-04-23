import type { KnowledgeBase } from "../../../api/context";
import { useState } from "react";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ManagedModel } from "../../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../../api/platform";
import { buildDeploymentForm, type DeploymentFormState } from "../deploymentEditor";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { t } from "../../../test/translation";
import {
  capabilitiesFixture,
  deploymentsFixture,
  embeddingsModelsFixture,
  knowledgeBasesFixture,
  llmModelsFixture,
  providersFixture,
} from "../../../test/platformControlFixtures";
import PlatformDeploymentForm from "./PlatformDeploymentForm";

function buildProvidersByCapability(capabilities: PlatformCapability[], providers: PlatformProvider[]): Record<string, PlatformProvider[]> {
  return Object.fromEntries(
    capabilities.map((capability) => [
      capability.capability,
      providers
        .filter((provider) => provider.capability === capability.capability)
        .map((provider) =>
          provider.capability === "llm_inference" || provider.capability === "embeddings"
            ? { ...provider, provider_origin: "cloud" as const }
            : provider,
        ),
    ]),
  );
}

function buildModelResourcesByCapability(): Record<string, ManagedModel[]> {
  return {
    llm_inference: llmModelsFixture,
    embeddings: embeddingsModelsFixture,
    vector_store: [],
  };
}

function buildKnowledgeBases(): KnowledgeBase[] {
  return knowledgeBasesFixture;
}

function DeploymentFormHarness(): JSX.Element {
  const [value, setValue] = useState<DeploymentFormState>(buildDeploymentForm(deploymentsFixture[0], capabilitiesFixture));

  return (
    <PlatformDeploymentForm
      value={value}
      capabilities={capabilitiesFixture}
      providersByCapability={buildProvidersByCapability(capabilitiesFixture, providersFixture)}
      modelResourcesByCapability={buildModelResourcesByCapability()}
      knowledgeBases={buildKnowledgeBases()}
      helperText="Editing deployment local-default."
      isSubmitting={false}
      submitLabel="Save deployment"
      submitBusyLabel="Saving..."
      onChange={setValue}
      onSubmit={(event) => event.preventDefault()}
    />
  );
}

function DeploymentFormWithOptionalCapabilityHarness(): JSX.Element {
  const capabilitiesWithOptional: PlatformCapability[] = [
    ...capabilitiesFixture,
    {
      capability: "sandbox_execution",
      display_name: "Sandbox execution",
      description: "Sandbox capability",
      required: false,
      active_provider: null,
    },
  ];
  const providersWithOptional: PlatformProvider[] = [
    ...providersFixture,
    {
      ...providersFixture[0],
      id: "provider-sandbox",
      slug: "sandbox-local",
      provider_key: "sandbox_local",
      provider_origin: "local",
      capability: "sandbox_execution",
      adapter_kind: "sandbox_http",
      display_name: "Sandbox local",
      description: "Primary sandbox provider.",
      endpoint_url: "http://sandbox:8080",
      healthcheck_url: "http://sandbox:8080/health",
    },
  ];
  const [value, setValue] = useState<DeploymentFormState>(buildDeploymentForm(deploymentsFixture[0], capabilitiesFixture));

  return (
    <PlatformDeploymentForm
      value={value}
      capabilities={capabilitiesWithOptional}
      providersByCapability={buildProvidersByCapability(capabilitiesWithOptional, providersWithOptional)}
      modelResourcesByCapability={buildModelResourcesByCapability()}
      knowledgeBases={buildKnowledgeBases()}
      helperText="Editing deployment local-default."
      isSubmitting={false}
      submitLabel="Save deployment"
      submitBusyLabel="Saving..."
      onChange={setValue}
      onSubmit={(event) => event.preventDefault()}
    />
  );
}

describe("PlatformDeploymentForm", () => {
  it("renders the deployment identity row first with editable slug and display name fields", async () => {
    await renderWithAppProviders(<DeploymentFormHarness />);

    const identityRow = screen.getByTestId("deployment-identity-row");
    expect(
      within(identityRow).getByLabelText(await t("platformControl.forms.deployment.slug")),
    ).toHaveValue("local-default");
    expect(
      within(identityRow).getByLabelText(await t("platformControl.forms.deployment.displayName")),
    ).toHaveValue("Local Default");
  });

  it("updates selected model resources and reassigns the default within the same binding row", async () => {
    await renderWithAppProviders(<DeploymentFormHarness />);

    const llmRow = screen.getByTestId("deployment-binding-row-llm_inference");
    const resourceButton = within(llmRow).getByRole("button", {
      name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" }),
    });
    const defaultSelect = within(llmRow).getByLabelText(
      await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "LLM inference" }),
    );

    expect(defaultSelect).toHaveValue("gpt-5");

    await userEvent.click(resourceButton);
    await userEvent.click(within(llmRow).getByLabelText("GPT-5"));

    expect(defaultSelect).toHaveValue("gpt-4.1");
    expect(within(llmRow).getByRole("button", {
      name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" }),
    })).toHaveTextContent("GPT-4.1");
  });

  it("lets superadmins add another capability row until all platform capabilities are included", async () => {
    await renderWithAppProviders(<DeploymentFormWithOptionalCapabilityHarness />);

    const addCapabilityRow = screen.getByTestId("deployment-add-capability-row");
    expect(within(addCapabilityRow).getByLabelText(await t("platformControl.forms.deployment.capability"))).toHaveValue(
      "sandbox_execution",
    );

    await userEvent.click(within(addCapabilityRow).getByRole("button", { name: await t("platformControl.actions.addCapability") }));

    expect(await screen.findByTestId("deployment-binding-row-sandbox_execution")).toBeVisible();
    expect(screen.queryByTestId("deployment-add-capability-row")).not.toBeInTheDocument();
  });
});
