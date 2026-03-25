import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import * as React from "react";
import PlatformDeploymentForm from "./PlatformDeploymentForm";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { t } from "../../../test/translation";
import {
  capabilitiesFixture,
  embeddingsModelsFixture,
  llmModelsFixture,
  providersFixture,
} from "../../../test/platformControlFixtures";
import type { DeploymentFormState } from "../utils";

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

function FormHarness({ initialValue }: { initialValue?: Partial<DeploymentFormState> }): JSX.Element {
  const [value, setValue] = React.useState<DeploymentFormState>(buildFormState(initialValue));

  return (
    <PlatformDeploymentForm
      value={value}
      capabilities={capabilitiesFixture}
      providersByCapability={{
        llm_inference: [providersFixture[0]],
        embeddings: [providersFixture[1]],
        vector_store: [providersFixture[2]],
      }}
      modelResourcesByCapability={{
        llm_inference: llmModelsFixture,
        embeddings: embeddingsModelsFixture,
      }}
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
  it("updates the selected provider and filters default resources to selected model resources", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<FormHarness />);

    await user.selectOptions(
      await screen.findByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "LLM inference" })),
      "provider-1",
    );
    await user.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" })),
      ["gpt-5"],
    );

    const providerSelect = screen.getByLabelText(
      await t("platformControl.forms.deployment.providerForCapability", { capability: "LLM inference" }),
    ) as HTMLSelectElement;
    expect(providerSelect.value).toBe("provider-1");

    const defaultSelect = screen.getByLabelText(
      await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "LLM inference" }),
    );
    const defaultOptions = within(defaultSelect).getAllByRole("option");
    expect(defaultOptions.map((option) => option.textContent)).toEqual(["Select an option", "GPT-5"]);
  });

  it("shows the vector namespace input only in dynamic namespace mode", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<FormHarness />);

    const selectionModeSelect = await screen.findByLabelText(await t("platformControl.forms.deployment.vectorSelectionMode"));
    expect(screen.getByLabelText(await t("platformControl.forms.deployment.explicitResources"))).toBeVisible();

    await user.selectOptions(selectionModeSelect, "dynamic_namespace");

    expect(screen.getByLabelText(await t("platformControl.forms.deployment.namespacePrefix"))).toBeVisible();
    expect(screen.queryByLabelText(await t("platformControl.forms.deployment.explicitResources"))).not.toBeInTheDocument();
  });
});
