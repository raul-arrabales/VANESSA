import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ModelCatalogList from "./ModelCatalogList";

describe("ModelCatalogList", () => {
  it("shows test actions only for eligible models when enabled", () => {
    render(
      <MemoryRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
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
          detailLabel="Open details"
          testLabel="Test model"
          validatedLabel="Validated"
          notValidatedLabel="Not validated"
          canTest
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Validated")).toBeInTheDocument();
    expect(screen.getByText("Not validated")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Test model" })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Test model" })).toHaveAttribute("href", "/control/models/gpt-4/test");
    expect(screen.getAllByRole("link", { name: "Open details" })).toHaveLength(2);
  });
});
