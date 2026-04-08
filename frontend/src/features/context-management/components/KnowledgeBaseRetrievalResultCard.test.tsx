import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { mapKnowledgeBaseQueryResultToDisplayItem } from "../../ai-shared/retrieval";
import { buildKnowledgeBaseQueryResult } from "../retrievalTestBuilders";
import { KnowledgeBaseRetrievalResultCard } from "./KnowledgeBaseRetrievalResultCard";

describe("KnowledgeBaseRetrievalResultCard", () => {
  it("renders hybrid score summaries and expanded chunk details", async () => {
    const onToggle = vi.fn();
    const result = buildKnowledgeBaseQueryResult({
      id: "doc-2",
      title: "FAQ",
      text:
        "Hybrid retrieval blends semantic recall with lexical precision so testers can inspect high-confidence overlap results first tail-marker-hybrid-beta",
      source_type: "local_directory",
      metadata: {
        document_id: "doc-2",
        chunk_index: 1,
        source_name: "FAQ folder",
        empty_field: "",
      },
      chunk_length_tokens: 18,
      relevance_score: 0.875,
      relevance_kind: "hybrid_score",
      relevance_components: {
        semantic_score: 0.75,
        keyword_score: 1,
      },
    });

    await renderWithAppProviders(
      <KnowledgeBaseRetrievalResultCard
        item={mapKnowledgeBaseQueryResultToDisplayItem(result, 0)}
        isExpanded
        onToggle={onToggle}
      />,
    );

    expect(screen.getByRole("heading", { name: "Chunk 1: FAQ" })).toBeVisible();
    expect(screen.getByText("Hybrid score: 0.875")).toBeVisible();
    expect(screen.getByText(result.text, { selector: "p" })).toBeVisible();
    expect(screen.getByLabelText("Chunk text")).toHaveDisplayValue(result.text);
    expect(screen.getByText("Chunk length: 18 tokens")).toBeVisible();
    expect(screen.getByText("Semantic score: 0.750")).toBeVisible();
    expect(screen.getByText("Keyword score: 1.000")).toBeVisible();
    expect(screen.getByText("document_id: doc-2")).toBeVisible();
    expect(screen.getByText("chunk_index: 1")).toBeVisible();
    expect(screen.queryByText(/^empty_field:/)).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Collapse retrieval result for Chunk 1: FAQ" }));

    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
