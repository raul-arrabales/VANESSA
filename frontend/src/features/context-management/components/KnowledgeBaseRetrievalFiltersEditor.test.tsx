import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { createEmptyMetadataEntry } from "../metadataEditor";
import { KnowledgeBaseRetrievalFiltersEditor } from "./KnowledgeBaseRetrievalFiltersEditor";

describe("KnowledgeBaseRetrievalFiltersEditor", () => {
  it("prevents duplicate property selections across active filter rows", async () => {
    const firstEntry = createEmptyMetadataEntry();
    const secondEntry = createEmptyMetadataEntry();
    const handleChange = vi.fn();

    const { rerender } = await renderWithAppProviders(
      <KnowledgeBaseRetrievalFiltersEditor
        schemaProperties={[
          { name: "category", data_type: "text" },
          { name: "published", data_type: "boolean" },
        ]}
        entries={[]}
        onChange={handleChange}
      />,
    );

    expect(screen.getByText("Metadata filters")).toBeVisible();
    expect(screen.getByText("No retrieval filters have been added yet.")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Add retrieval filter" }));

    expect(handleChange).toHaveBeenCalledWith([expect.objectContaining({ propertyName: "", value: "" })]);

    rerender(
      <KnowledgeBaseRetrievalFiltersEditor
        schemaProperties={[
          { name: "category", data_type: "text" },
          { name: "published", data_type: "boolean" },
        ]}
        entries={[
          { ...firstEntry, propertyName: "category", value: "guide" },
          { ...secondEntry, propertyName: "", value: "" },
        ]}
        onChange={handleChange}
      />,
    );

    const propertyInputs = screen.getAllByLabelText("Property name");
    const secondPropertySelect = propertyInputs[1];

    expect(within(secondPropertySelect).queryByRole("option", { name: "category" })).toBeNull();
    expect(within(secondPropertySelect).getByRole("option", { name: "published" })).toBeVisible();
  });
});
