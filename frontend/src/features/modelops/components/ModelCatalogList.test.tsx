import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { expectNamedIconAction, expectNoGenericCompactActions } from "../../../test/compactRegistryAssertions";
import ModelCatalogList from "./ModelCatalogList";

describe("ModelCatalogList", () => {
  it("shows test actions only for eligible models when enabled", async () => {
    await renderWithAppProviders(
      <ModelCatalogList
        models={[
          {
            id: "gpt-4",
            name: "GPT-4",
            provider: "openai_compatible",
            backend: "external_api",
            source: "external_provider",
            availability: "online_only",
            task_key: "llm",
            lifecycle_state: "registered",
            is_validation_current: true,
            last_validation_status: "success",
          },
          {
            id: "draft-model",
            name: "Draft model",
            provider: "openai_compatible",
            backend: "external_api",
            source: "external_provider",
            availability: "online_only",
            task_key: "llm",
            lifecycle_state: "created",
            is_validation_current: false,
            last_validation_status: null,
          },
        ]}
        emptyLabel="Empty"
        validatedLabel="Validated"
        notValidatedLabel="Not validated"
        canTest
      />
    );

    expect(screen.getByText("Validated")).toBeInTheDocument();
    expect(screen.getByText("Not validated")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Test model: GPT-4" })).toHaveLength(1);
    expect(expectNamedIconAction("link", "Test model: GPT-4")).toHaveAttribute("href", "/control/models/gpt-4/test");
    expect(expectNamedIconAction("link", "Open details: GPT-4")).toHaveAttribute("href", "/control/models/gpt-4");
    expect(expectNamedIconAction("link", "Open details: Draft model")).toHaveAttribute("href", "/control/models/draft-model");
    expectNoGenericCompactActions(["Test", "Open details"]);
  });
});
