import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { buildKnowledgeBaseQueryResult } from "../retrievalTestBuilders";
import { KnowledgeBaseRetrievalResults } from "./KnowledgeBaseRetrievalResults";

describe("KnowledgeBaseRetrievalResults", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders the grouped retrieval run summary and result cards", async () => {
    await renderWithAppProviders(
      <KnowledgeBaseRetrievalResults
        retrievalRun={{
          results: [
            buildKnowledgeBaseQueryResult({
              id: "doc-1",
              title: "Architecture Overview",
              text: "Result preview text for retrieval testing tail-marker-render",
              relevance_score: 0.742,
            }),
          ],
          resultCount: 1,
          durationMs: 360,
          completedQueryId: 1,
        }}
      />,
    );

    expect(screen.getByText("1 retrieval result(s)")).toBeVisible();
    expect(screen.getByText("Completed in 360 ms.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Expand retrieval result for Chunk 1: Architecture Overview" })).toBeVisible();
  });

  it("renders no summary content before the first successful retrieval", async () => {
    await renderWithAppProviders(<KnowledgeBaseRetrievalResults retrievalRun={null} />);

    expect(screen.queryByText(/retrieval result\(s\)/i)).toBeNull();
    expect(screen.queryByText(/Completed in/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /Expand retrieval result for/i })).toBeNull();
  });
});
