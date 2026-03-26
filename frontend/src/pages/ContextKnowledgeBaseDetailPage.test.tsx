import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

const contextApiMocks = vi.hoisted(() => ({
  getKnowledgeBase: vi.fn(async () => ({
    id: "kb-primary",
    slug: "product-docs",
    display_name: "Product Docs",
    description: "docs",
    index_name: "kb_product_docs",
    backing_provider_key: "weaviate_local",
    lifecycle_state: "active",
    sync_status: "ready",
    eligible_for_binding: true,
    last_sync_at: "2026-03-26T20:00:00+00:00",
    last_sync_error: null,
    last_sync_summary: "Managed knowledge base index is ready.",
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
      source_type: "local_directory",
      source_name: "Docs folder",
      uri: null,
      text: "Hello world",
      metadata: {},
      chunk_count: 1,
      source_id: "source-1",
      source_path: "product_docs/overview.txt",
      source_document_key: "product_docs/overview.txt#0",
      managed_by_source: true,
    },
  ]),
  listKnowledgeSources: vi.fn(async () => [
    {
      id: "source-1",
      knowledge_base_id: "kb-primary",
      source_type: "local_directory",
      display_name: "Docs folder",
      relative_path: "product_docs",
      include_globs: ["**/*.md"],
      exclude_globs: [],
      lifecycle_state: "active",
      last_sync_status: "ready",
      last_sync_at: "2026-03-26T20:10:00+00:00",
      last_sync_error: null,
    },
  ]),
  listKnowledgeSyncRuns: vi.fn(async () => [
    {
      id: "run-1",
      knowledge_base_id: "kb-primary",
      source_id: "source-1",
      source_display_name: "Docs folder",
      status: "ready",
      scanned_file_count: 1,
      changed_file_count: 1,
      deleted_file_count: 0,
      created_document_count: 1,
      updated_document_count: 0,
      deleted_document_count: 0,
      error_summary: null,
      started_at: "2026-03-26T20:10:00+00:00",
      finished_at: "2026-03-26T20:10:01+00:00",
    },
  ]),
  queryKnowledgeBase: vi.fn(async () => ({
    knowledge_base_id: "kb-primary",
    retrieval: { index: "kb_product_docs", result_count: 1, top_k: 5 },
    results: [
      {
        id: "doc-1",
        title: "Architecture Overview",
        snippet: "Retrieved snippet",
        uri: "https://example.com/overview",
        source_type: "manual",
        metadata: {},
        score: 0.91,
        score_kind: "similarity",
      },
    ],
  })),
  resyncKnowledgeBase: vi.fn(async () => ({
    id: "kb-primary",
    slug: "product-docs",
    display_name: "Product Docs",
    description: "docs",
    index_name: "kb_product_docs",
    backing_provider_key: "weaviate_local",
    lifecycle_state: "active",
    sync_status: "ready",
    eligible_for_binding: true,
    last_sync_at: "2026-03-26T21:00:00+00:00",
    last_sync_error: null,
    last_sync_summary: "Resynced 1 document(s) and 1 chunk(s).",
    schema: {},
    document_count: 1,
    deployment_usage: [],
  })),
  updateKnowledgeBase: vi.fn(),
  createKnowledgeSource: vi.fn(),
  updateKnowledgeSource: vi.fn(),
  deleteKnowledgeSource: vi.fn(),
  syncKnowledgeSource: vi.fn(async () => ({
    knowledge_base: {
      id: "kb-primary",
      slug: "product-docs",
      display_name: "Product Docs",
      description: "docs",
      index_name: "kb_product_docs",
      backing_provider_key: "weaviate_local",
      lifecycle_state: "active",
      sync_status: "ready",
      eligible_for_binding: true,
      last_sync_at: "2026-03-26T21:00:00+00:00",
      last_sync_error: null,
      last_sync_summary: "Source 'Docs folder' synced 1 created, 0 updated, 0 deleted document(s).",
      schema: {},
      document_count: 1,
      deployment_usage: [],
    },
    source: {
      id: "source-1",
      knowledge_base_id: "kb-primary",
      source_type: "local_directory",
      display_name: "Docs folder",
      relative_path: "product_docs",
      include_globs: ["**/*.md"],
      exclude_globs: [],
      lifecycle_state: "active",
      last_sync_status: "ready",
      last_sync_at: "2026-03-26T21:00:00+00:00",
      last_sync_error: null,
    },
    sync_run: {
      id: "run-2",
      knowledge_base_id: "kb-primary",
      source_id: "source-1",
      source_display_name: "Docs folder",
      status: "ready",
      scanned_file_count: 1,
      changed_file_count: 1,
      deleted_file_count: 0,
      created_document_count: 1,
      updated_document_count: 0,
      deleted_document_count: 0,
      error_summary: null,
      started_at: "2026-03-26T21:00:00+00:00",
      finished_at: "2026-03-26T21:00:01+00:00",
    },
  })),
  createKnowledgeBaseDocument: vi.fn(),
  updateKnowledgeBaseDocument: vi.fn(),
  deleteKnowledgeBaseDocument: vi.fn(),
  uploadKnowledgeBaseDocuments: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
}));

vi.mock("../api/context", () => contextApiMocks);

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

  it("renders knowledge-base metadata, sources, sync history, and retrieval results", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/context/:knowledgeBaseId" element={<ContextKnowledgeBaseDetailPage />} />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    expect(await screen.findByRole("heading", { name: "Product Docs" })).toBeVisible();
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText(/Local Default/)).toBeVisible();
    expect(screen.getByText(/Managed knowledge base index is ready\./i)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Sources" })).toBeVisible();
    expect(screen.getAllByText("Docs folder").length).toBeGreaterThan(0);
    expect(screen.getByText(/Managed by Docs folder/)).toBeVisible();
    expect(screen.getAllByText(/\.pdf/).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Sync history" })).toBeVisible();
    expect(screen.getByText(/Scanned 1 file/)).toBeVisible();

    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    expect(await screen.findByText("Retrieved snippet")).toBeVisible();
    expect(contextApiMocks.queryKnowledgeBase).toHaveBeenCalledWith(
      "kb-primary",
      { query_text: "How does retrieval work?", top_k: 5 },
      "token",
    );
  });

  it("lets superadmins resync the knowledge base", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/context/:knowledgeBaseId" element={<ContextKnowledgeBaseDetailPage />} />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Resync knowledge base" }));

    await waitFor(() => expect(contextApiMocks.resyncKnowledgeBase).toHaveBeenCalledWith("kb-primary", "token"));
  });

  it("lets superadmins sync a managed source", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/context/:knowledgeBaseId" element={<ContextKnowledgeBaseDetailPage />} />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));

    await waitFor(() => expect(contextApiMocks.syncKnowledgeSource).toHaveBeenCalledWith("kb-primary", "source-1", "token"));
  });
});
