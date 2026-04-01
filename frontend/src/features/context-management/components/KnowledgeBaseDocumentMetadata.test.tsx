import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { buildKnowledgeBaseDocumentExcerpt } from "../documentPresentation";
import { KnowledgeBaseDocumentMetadata } from "./KnowledgeBaseDocumentMetadata";

const sourceManagedDocument = {
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

const manualDocument = {
  id: "doc-2",
  knowledge_base_id: "kb-primary",
  title: "Manual Note",
  source_type: "manual",
  source_name: "Operator note",
  uri: "https://example.com/manual-note",
  text: "A manually curated note for testing uploads and editing.",
  metadata: {},
  chunk_count: 1,
  source_id: null,
  source_path: null,
  source_document_key: null,
  managed_by_source: false,
};

describe("KnowledgeBaseDocumentMetadata", () => {
  it("renders source-managed document metadata consistently", async () => {
    await renderWithAppProviders(<KnowledgeBaseDocumentMetadata document={sourceManagedDocument} showStatusChip />);

    expect(screen.getByRole("heading", { name: "Architecture Overview" })).toBeVisible();
    expect(screen.getByText("Managed by Docs folder (product_docs/overview.txt)")).toBeVisible();
    expect(screen.getByText("Source-managed")).toBeVisible();
    expect(screen.getByText("Source path: product_docs/overview.txt")).toBeVisible();
    expect(screen.getByText("Chunk count: 2")).toBeVisible();
  });

  it("renders manual document metadata consistently", async () => {
    await renderWithAppProviders(<KnowledgeBaseDocumentMetadata document={manualDocument} showStatusChip />);

    expect(screen.getByRole("heading", { name: "Manual Note" })).toBeVisible();
    expect(screen.getByText("Operator note")).toBeVisible();
    expect(screen.getByText("Manual document")).toBeVisible();
    expect(screen.getByText("https://example.com/manual-note")).toBeVisible();
    expect(screen.getByText("Chunk count: 1")).toBeVisible();
  });

  it("builds consistent excerpts for document previews", () => {
    expect(buildKnowledgeBaseDocumentExcerpt(" 1234567890 ", 6)).toBe("123...");
    expect(buildKnowledgeBaseDocumentExcerpt("short text", 20)).toBe("short text");
  });
});
