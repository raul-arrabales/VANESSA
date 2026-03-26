import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import ContextKnowledgeBaseDetailPage from "./ContextKnowledgeBaseDetailPage";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("../api/context", () => ({
  getKnowledgeBase: vi.fn(async () => ({
    id: "kb-primary",
    slug: "product-docs",
    display_name: "Product Docs",
    description: "docs",
    index_name: "kb_product_docs",
    backing_provider_key: "weaviate_local",
    lifecycle_state: "active",
    sync_status: "ready",
    schema: {},
    document_count: 1,
    deployment_usage: [
      {
        deployment_profile: {
          id: "deployment-1",
          slug: "local-default",
          display_name: "Local Default",
        },
        capability: "vector_store",
      },
    ],
  })),
  listKnowledgeBaseDocuments: vi.fn(async () => [
    {
      id: "doc-1",
      knowledge_base_id: "kb-primary",
      title: "Architecture Overview",
      source_type: "manual",
      source_name: "Manual",
      uri: null,
      text: "Hello world",
      metadata: {},
      chunk_count: 1,
    },
  ]),
  updateKnowledgeBase: vi.fn(),
  createKnowledgeBaseDocument: vi.fn(),
  updateKnowledgeBaseDocument: vi.fn(),
  deleteKnowledgeBaseDocument: vi.fn(),
  uploadKnowledgeBaseDocuments: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
}));

describe("ContextKnowledgeBaseDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };
  });

  it("renders knowledge-base metadata and documents", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/context/:knowledgeBaseId" element={<ContextKnowledgeBaseDetailPage />} />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    expect(await screen.findByRole("heading", { name: "Product Docs" })).toBeVisible();
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText(/Local Default/)).toBeVisible();
  });
});
