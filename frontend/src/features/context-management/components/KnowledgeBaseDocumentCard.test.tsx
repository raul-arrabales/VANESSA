import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { KnowledgeBaseDocumentCard } from "./KnowledgeBaseDocumentCard";

const document = {
  id: "doc-1",
  knowledge_base_id: "kb-primary",
  title: "Architecture Overview",
  source_type: "local_directory",
  source_name: "Docs folder",
  uri: null,
  text: "Hello world from source managed content",
  metadata: {},
  chunk_count: 2,
  source_id: "source-1",
  source_path: "product_docs/overview.txt",
  source_document_key: "product_docs/overview.txt#0",
  managed_by_source: true,
};

describe("KnowledgeBaseDocumentCard", () => {
  it("renders shared metadata, excerpt, and footer actions", async () => {
    await renderWithAppProviders(
      <KnowledgeBaseDocumentCard
        document={document}
        excerptLength={12}
        showStatusChip
        actions={<button type="button">Open text</button>}
      />,
    );

    expect(screen.getByRole("heading", { name: "Architecture Overview" })).toBeVisible();
    expect(screen.getByText("Managed by Docs folder (product_docs/overview.txt)")).toBeVisible();
    expect(screen.getByText("Hello wor...")).toBeVisible();
    expect(screen.getByRole("button", { name: "Open text" })).toBeVisible();
  });
});
