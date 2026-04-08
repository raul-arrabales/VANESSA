import type { FormEvent } from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { KnowledgeBaseRetrievalSettingsForm } from "./KnowledgeBaseRetrievalSettingsForm";

describe("KnowledgeBaseRetrievalSettingsForm", () => {
  it("shows hybrid alpha only for hybrid search and submits the configured values", async () => {
    const handleSubmit = vi.fn(async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
    });
    const handleQueryChange = vi.fn();
    const handleTopKChange = vi.fn();
    const handleSearchMethodChange = vi.fn();
    const handleHybridAlphaChange = vi.fn();
    const handleQueryPreprocessingChange = vi.fn();

    const { rerender } = await renderWithAppProviders(
      <KnowledgeBaseRetrievalSettingsForm
        retrievalQuery="How does retrieval work?"
        retrievalTopK="5"
        retrievalSearchMethod="semantic"
        retrievalHybridAlpha="0.5"
        retrievalQueryPreprocessing="none"
        isQuerying={false}
        onQueryChange={handleQueryChange}
        onTopKChange={handleTopKChange}
        onSearchMethodChange={handleSearchMethodChange}
        onHybridAlphaChange={handleHybridAlphaChange}
        onQueryPreprocessingChange={handleQueryPreprocessingChange}
        onSubmit={handleSubmit}
      />,
    );

    expect(screen.queryByLabelText("Hybrid alpha")).toBeNull();

    rerender(
      <KnowledgeBaseRetrievalSettingsForm
        retrievalQuery="How does retrieval work?"
        retrievalTopK="5"
        retrievalSearchMethod="hybrid"
        retrievalHybridAlpha="0.5"
        retrievalQueryPreprocessing="none"
        isQuerying={false}
        onQueryChange={handleQueryChange}
        onTopKChange={handleTopKChange}
        onSearchMethodChange={handleSearchMethodChange}
        onHybridAlphaChange={handleHybridAlphaChange}
        onQueryPreprocessingChange={handleQueryPreprocessingChange}
        onSubmit={handleSubmit}
      />,
    );

    await userEvent.clear(screen.getByLabelText("Hybrid alpha"));
    await userEvent.type(screen.getByLabelText("Hybrid alpha"), "0.65");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    expect(screen.getByLabelText("Hybrid alpha")).toBeVisible();
    expect(handleHybridAlphaChange).toHaveBeenCalled();
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });
});
