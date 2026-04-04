import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { ContextKnowledgeBaseWorkspaceFrame } from "./ContextKnowledgeBaseWorkspaceFrame";

const knowledgeBase = {
  id: "kb-primary",
  slug: "product-docs",
  display_name: "Product Docs",
  description: "docs",
  index_name: "kb_product_docs",
  backing_provider_instance_id: "provider-2",
  backing_provider_key: "weaviate_local",
  backing_provider: null,
  lifecycle_state: "active",
  sync_status: "ready",
  eligible_for_binding: true,
  schema: {},
  vectorization: {
    mode: "vanessa_embeddings",
    supports_named_vectors: true,
  },
  chunking: {
    strategy: "fixed_length",
    config: {
      unit: "tokens",
      chunk_length: 300,
      chunk_overlap: 60,
    },
  },
  document_count: 0,
  deployment_usage: [],
};

describe("ContextKnowledgeBaseWorkspaceFrame", () => {
  it("renders the shared workspace layout and loading panel", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route
          path="/control/context/:knowledgeBaseId"
          element={
            <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={knowledgeBase} loading>
              {() => <p>frame-child</p>}
            </ContextKnowledgeBaseWorkspaceFrame>
          }
        />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    expect(screen.getByRole("heading", { name: "Product Docs" })).toBeVisible();
    expect(screen.getByText("Loading knowledge bases...")).toBeVisible();
    expect(screen.getByText("frame-child")).toBeVisible();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Manage Sources" })).toHaveAttribute("href", "/control/context/kb-primary/sources");
  });

  it("guards child rendering when the knowledge base is unavailable", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route
          path="/control/context/:knowledgeBaseId"
          element={
            <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={null} loading={false}>
              {() => <p>frame-child</p>}
            </ContextKnowledgeBaseWorkspaceFrame>
          }
        />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    expect(screen.queryByText("frame-child")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to knowledge bases" })).toHaveAttribute("href", "/control/context");
  });
});
