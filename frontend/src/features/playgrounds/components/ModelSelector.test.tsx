import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ModelSelector from "./ModelSelector";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

describe("ModelSelector", () => {
  it("localizes the label, aria label, and empty option", async () => {
    await renderWithAppProviders(
      <ModelSelector
        models={[]}
        value=""
        isLoading={false}
        disabled={false}
        onChange={vi.fn()}
      />,
      { language: "es" },
    );

    expect(screen.getByText("Modelo")).toBeVisible();
    expect(screen.getByLabelText("Modelo")).toHaveDisplayValue("No hay modelos habilitados");
  });
});
