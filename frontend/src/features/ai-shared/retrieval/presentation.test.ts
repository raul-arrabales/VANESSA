import { describe, expect, it } from "vitest";
import { buildKnowledgeBaseQueryResult } from "../../context-management/retrievalTestBuilders";
import {
  buildRetrievalPreview,
  getRetrievalComponentScoreRows,
  getRetrievalScoreKind,
  getVisibleRetrievalMetadataEntries,
  mapKnowledgeBaseQueryResultToDisplayItem,
  mapPlaygroundKnowledgeSourceToDisplayItem,
  mapRetrievalSourceToDisplayItem,
  shouldShowHybridAlphaControl,
} from "./presentation";

describe("retrieval presentation", () => {
  it("builds previews from the first 24 tokens", () => {
    expect(
      buildRetrievalPreview(
        "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive",
      ),
    ).toBe(
      "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour…",
    );
  });

  it("filters unset metadata entries and formats visible values", () => {
    expect(
      getVisibleRetrievalMetadataEntries({
        document_id: "doc-1",
        chunk_index: 0,
        empty_field: "",
        missing_field: undefined,
        null_field: null,
        flags: { reviewed: true },
      }),
    ).toEqual([
      { key: "document_id", value: "doc-1" },
      { key: "chunk_index", value: "0" },
      { key: "flags", value: JSON.stringify({ reviewed: true }) },
    ]);
  });

  it("returns score labels and hybrid component rows from normalized or provider score kinds", () => {
    const hybridResult = buildKnowledgeBaseQueryResult({
      relevance_kind: "hybrid_score",
      relevance_components: {
        semantic_score: 0.81,
        keyword_score: 0.67,
      },
    });

    expect(getRetrievalScoreKind(hybridResult)).toBe("hybrid_score");
    expect(getRetrievalScoreKind({ score_kind: "bm25" })).toBe("keyword_score");
    expect(getRetrievalComponentScoreRows(hybridResult)).toEqual([
      { kind: "semantic_score", value: 0.81 },
      { kind: "keyword_score", value: 0.67 },
    ]);
    expect(shouldShowHybridAlphaControl("hybrid")).toBe(true);
    expect(shouldShowHybridAlphaControl("semantic")).toBe(false);
  });

  it("maps KB retrieval results into numbered display items", () => {
    const item = mapKnowledgeBaseQueryResultToDisplayItem(
      buildKnowledgeBaseQueryResult({
        id: "doc-2",
        title: "FAQ",
        text:
          "Top matches should appear first so reviewers can quickly inspect the most relevant chunk before opening lower-ranked context entries tail-marker-beta",
        relevance_score: 0.913,
      }),
      1,
    );

    expect(item.displayTitle).toBe("Chunk 2: FAQ");
    expect(item.displayScoreKind).toBe("similarity");
    expect(item.displayScoreValue).toBe(0.913);
    expect(item.displaySnippet).toContain("Top matches should appear first");
    expect(item.displayMetadataEntries).toEqual([
      { key: "document_id", value: "doc-1" },
      { key: "chunk_index", value: "0" },
      { key: "source_name", value: "Docs folder" },
    ]);
    expect(item.isExpandable).toBe(true);
  });

  it("uses provided snippets for generic retrieval source display items", () => {
    const item = mapRetrievalSourceToDisplayItem(
      {
        id: "source-1",
        title: "Architecture Overview",
        snippet: "Short snippet from backend source mapping.",
        text: "Longer source text that should not be used when snippet is already present.",
        metadata: {},
        score: 0.92,
        score_kind: "similarity",
      },
      { ordinal: 1, ordinalPrefix: "Source" },
    );

    expect(item.displayTitle).toBe("Source 1: Architecture Overview");
    expect(item.displaySnippet).toBe("Short snippet from backend source mapping.");
    expect(item.displayScoreValue).toBe(0.92);
  });

  it("maps playground knowledge sources into compact display items using provided snippets", () => {
    const item = mapPlaygroundKnowledgeSourceToDisplayItem({
      id: "doc-1",
      title: "Architecture Overview",
      snippet: "Shared snippet from retrieval projection.",
      text: "Longer source text that should not replace the snippet.",
      metadata: { source_name: "Docs folder", ignored_empty: "" },
      score: 7.2,
      score_kind: "bm25",
      relevance_kind: "keyword_score",
    });

    expect(item.displayTitle).toBe("Architecture Overview");
    expect(item.displaySnippet).toBe("Shared snippet from retrieval projection.");
    expect(item.displayScoreKind).toBe("keyword_score");
    expect(item.displayMetadataEntries).toEqual([{ key: "source_name", value: "Docs folder" }]);
  });
});
