import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { KnowledgeBaseChunkingEditor } from "./KnowledgeBaseChunkingEditor";

describe("KnowledgeBaseChunkingEditor", () => {
  it("renders the reusable create-mode chunking UI with hint and inline error", async () => {
    const onChangeField = vi.fn();

    await renderWithAppProviders(
      <KnowledgeBaseChunkingEditor
        form={{
          strategy: "fixed_length",
          chunkLength: "300",
          chunkOverlap: "60",
        }}
        editable
        showStrategySelector
        showDescription
        showUnitLabel
        showConstraintsHint
        inlineSafeLimitErrorMessage="Chunk length 300 exceeds the selected embeddings model safe maximum of 254 tokens."
        constraints={{
          max_input_tokens: 256,
          special_tokens_per_input: 2,
          safe_chunk_length_max: 254,
        }}
        onChangeField={onChangeField}
      />,
    );

    expect(screen.getByLabelText("Chunking strategy")).toHaveValue("fixed_length");
    expect(screen.getByText(/supports up to 254 chunk tokens safely/i)).toBeVisible();
    expect(screen.getByText(/chunk length 300 exceeds the selected embeddings model safe maximum/i)).toBeVisible();

    await userEvent.clear(screen.getByLabelText("Chunk length"));
    await userEvent.type(screen.getByLabelText("Chunk length"), "254");

    expect(onChangeField).toHaveBeenCalled();
  });

  it("supports read-only editable-before-ingest and locked-after-ingest states", async () => {
    const { rerender } = await renderWithAppProviders(
      <KnowledgeBaseChunkingEditor
        form={{
          strategy: "fixed_length",
          chunkLength: "254",
          chunkOverlap: "60",
        }}
        editable={false}
        showInputsWhenReadOnly
        editabilityMessage="editable_before_ingest"
      />,
    );

    expect(screen.getByText("Chunking can still be edited because this knowledge base has not ingested any documents yet.")).toBeVisible();
    expect(screen.getByLabelText("Chunk length")).toBeDisabled();
    expect(screen.getByLabelText("Chunk overlap")).toBeDisabled();

    rerender(
      <KnowledgeBaseChunkingEditor
        form={{
          strategy: "fixed_length",
          chunkLength: "254",
          chunkOverlap: "60",
        }}
        editable={false}
        editabilityMessage="locked_after_ingest"
      />,
    );

    expect(screen.getByText("Chunking is locked after documents have been ingested.")).toBeVisible();
    expect(screen.queryByLabelText("Chunk length")).not.toBeInTheDocument();
  });
});
