import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import KnowledgeBaseSelector from "./KnowledgeBaseSelector";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

describe("KnowledgeBaseSelector", () => {
  it("localizes the label, aria label, and placeholder", async () => {
    await renderWithAppProviders(
      <KnowledgeBaseSelector
        knowledgeBases={[]}
        value=""
        disabled={false}
        isLoading={false}
        onChange={vi.fn()}
      />,
      { language: "es" },
    );

    expect(screen.getByText("Base de conocimiento")).toBeVisible();
    expect(screen.getByLabelText("Base de conocimiento")).toHaveDisplayValue("Selecciona una base de conocimiento");
  });
});
