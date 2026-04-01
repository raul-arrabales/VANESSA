import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import ContextKnowledgeBaseDetailPage from "./ContextKnowledgeBaseDetailPage";
import ContextKnowledgeBaseSourcesPage from "../features/context-management/pages/ContextKnowledgeBaseSourcesPage";
import ContextKnowledgeBaseRetrievalPage from "../features/context-management/pages/ContextKnowledgeBaseRetrievalPage";
import ContextKnowledgeBaseUploadPage from "../features/context-management/pages/ContextKnowledgeBaseUploadPage";
import ContextKnowledgeBaseDocumentsPage from "../features/context-management/pages/ContextKnowledgeBaseDocumentsPage";
import ContextKnowledgeBaseDocumentViewPage from "../features/context-management/pages/ContextKnowledgeBaseDocumentViewPage";

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
    backing_provider_instance_id: "provider-2",
    backing_provider_key: "weaviate_local",
    backing_provider: {
      id: "provider-2",
      slug: "weaviate-local",
      provider_key: "weaviate_local",
      display_name: "Weaviate local",
      enabled: true,
      capability: "vector_store",
    },
    lifecycle_state: "active",
    sync_status: "ready",
    eligible_for_binding: true,
    last_sync_at: "2026-03-26T20:00:00+00:00",
    last_sync_error: null,
    last_sync_summary: "Managed knowledge base index is ready.",
    schema: {},
    vectorization: {
      mode: "vanessa_embeddings",
      embedding_provider_instance_id: "embedding-provider-1",
      embedding_resource_id: "text-embedding-3-small",
      embedding_provider: {
        id: "embedding-provider-1",
        display_name: "Embeddings local",
        provider_key: "openai_compatible_cloud_embeddings",
      },
      embedding_resource: {
        id: "text-embedding-3-small",
        display_name: "text-embedding-3-small",
        provider_resource_id: "text-embedding-3-small",
      },
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
    document_count: 2,
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
      text: "Hello world from source managed content",
      metadata: {},
      chunk_count: 1,
      source_id: "source-1",
      source_path: "product_docs/overview.txt",
      source_document_key: "product_docs/overview.txt#0",
      managed_by_source: true,
    },
    {
      id: "doc-2",
      knowledge_base_id: "kb-primary",
      title: "Manual Note",
      source_type: "manual",
      source_name: "Operator note",
      uri: "https://example.com/manual-note",
      text: "A manually curated note for testing uploads and editing.",
      metadata: {},
      chunk_count: 2,
      source_id: null,
      source_path: null,
      source_document_key: null,
      managed_by_source: false,
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
      exclude_globs: [] as string[],
      lifecycle_state: "active",
      last_sync_status: "ready",
      last_sync_at: "2026-03-26T20:10:00+00:00",
      last_sync_error: null,
    },
  ]),
  getKnowledgeSourceDirectories: vi.fn(async (_token: string, options?: { rootId?: string | null; relativePath?: string | null }) => ({
    roots: [{ id: "root-1", display_name: "/context_sources" }],
    selected_root_id: "root-1",
    current_relative_path: options?.relativePath ?? "",
    parent_relative_path: options?.relativePath === "product_docs" ? "" : null,
    directories:
      options?.relativePath === "product_docs"
        ? [{ name: "guides", relative_path: "product_docs/guides" }]
        : [{ name: "product_docs", relative_path: "product_docs" }],
  })),
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
    backing_provider_instance_id: "provider-2",
    backing_provider_key: "weaviate_local",
    backing_provider: {
      id: "provider-2",
      slug: "weaviate-local",
      provider_key: "weaviate_local",
      display_name: "Weaviate local",
      enabled: true,
      capability: "vector_store",
    },
    lifecycle_state: "active",
    sync_status: "ready",
    eligible_for_binding: true,
    last_sync_at: "2026-03-26T21:00:00+00:00",
    last_sync_error: null,
    last_sync_summary: "Resynced 2 document(s) and 3 chunk(s).",
    schema: {},
    vectorization: {
      mode: "vanessa_embeddings",
      embedding_provider_instance_id: "embedding-provider-1",
      embedding_resource_id: "text-embedding-3-small",
      embedding_provider: {
        id: "embedding-provider-1",
        display_name: "Embeddings local",
        provider_key: "openai_compatible_cloud_embeddings",
      },
      embedding_resource: {
        id: "text-embedding-3-small",
        display_name: "text-embedding-3-small",
        provider_resource_id: "text-embedding-3-small",
      },
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
    document_count: 2,
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
      backing_provider_instance_id: "provider-2",
      backing_provider_key: "weaviate_local",
      backing_provider: {
        id: "provider-2",
        slug: "weaviate-local",
        provider_key: "weaviate_local",
        display_name: "Weaviate local",
        enabled: true,
        capability: "vector_store",
      },
      lifecycle_state: "active",
      sync_status: "ready",
      eligible_for_binding: true,
      last_sync_at: "2026-03-26T21:00:00+00:00",
      last_sync_error: null,
      last_sync_summary: "Source 'Docs folder' synced 1 created, 0 updated, 0 deleted document(s).",
      schema: {},
      vectorization: {
        mode: "vanessa_embeddings",
        embedding_provider_instance_id: "embedding-provider-1",
        embedding_resource_id: "text-embedding-3-small",
        embedding_provider: {
          id: "embedding-provider-1",
          display_name: "Embeddings local",
          provider_key: "openai_compatible_cloud_embeddings",
        },
        embedding_resource: {
          id: "text-embedding-3-small",
          display_name: "text-embedding-3-small",
          provider_resource_id: "text-embedding-3-small",
        },
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
      document_count: 2,
      deployment_usage: [],
    },
    source: {
      id: "source-1",
      knowledge_base_id: "kb-primary",
      source_type: "local_directory",
      display_name: "Docs folder",
      relative_path: "product_docs",
      include_globs: ["**/*.md"],
      exclude_globs: [] as string[],
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

async function renderContextWorkspace(route: string): Promise<void> {
  await renderWithAppProviders(
    <Routes>
      <Route path="/control/context/:knowledgeBaseId" element={<ContextKnowledgeBaseDetailPage />} />
      <Route path="/control/context/:knowledgeBaseId/sources" element={<ContextKnowledgeBaseSourcesPage />} />
      <Route path="/control/context/:knowledgeBaseId/retrieval" element={<ContextKnowledgeBaseRetrievalPage />} />
      <Route path="/control/context/:knowledgeBaseId/upload" element={<ContextKnowledgeBaseUploadPage />} />
      <Route path="/control/context/:knowledgeBaseId/documents" element={<ContextKnowledgeBaseDocumentsPage />} />
      <Route path="/control/context/:knowledgeBaseId/documents/:documentId/view" element={<ContextKnowledgeBaseDocumentViewPage />} />
    </Routes>,
    { route },
  );
}

describe("ContextKnowledgeBaseWorkspace pages", () => {
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

  it("renders the overview page with metadata and workspace subnav", async () => {
    await renderContextWorkspace("/control/context/kb-primary");

    expect(await screen.findByRole("heading", { name: "Product Docs" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Overview" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Manage Sources" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Upload Documents" })).toBeVisible();
    expect(screen.getByText(/Weaviate local/)).toBeVisible();
    expect(screen.getByText(/Embeddings local/)).toBeVisible();
    expect(screen.getByText(/text-embedding-3-small/)).toBeVisible();
    expect(screen.getByText(/Fixed length/)).toBeVisible();
    expect(screen.getByText(/Chunk length: 300/)).toBeVisible();
    expect(screen.getByText(/Chunk overlap: 60/)).toBeVisible();
    expect(screen.getByText(/Local Default/)).toBeVisible();
    expect(screen.getByText(/Managed knowledge base index is ready\./i)).toBeVisible();
  });

  it("lets superadmins resync from the overview page", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary");

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Resync knowledge base" }));

    await waitFor(() => expect(contextApiMocks.resyncKnowledgeBase).toHaveBeenCalledWith("kb-primary", "token"));
  });

  it("renders the sources page and lets superadmins browse and sync sources", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/sources");

    expect(await screen.findByRole("heading", { name: "Sources" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Sync history" })).toBeVisible();
    expect(screen.getByText(/Scanned 1 file/)).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Browse" }));
    await userEvent.click(await screen.findByRole("button", { name: "product_docs" }));
    await userEvent.click(screen.getByRole("button", { name: "Use current directory" }));
    expect(screen.getByDisplayValue("product_docs")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    await waitFor(() => expect(contextApiMocks.syncKnowledgeSource).toHaveBeenCalledWith("kb-primary", "source-1", "token"));
  });

  it("renders the retrieval page and runs retrieval queries", async () => {
    await renderContextWorkspace("/control/context/kb-primary/retrieval");

    expect(await screen.findByRole("heading", { name: "Test retrieval" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    expect(await screen.findByText("Retrieved snippet")).toBeVisible();
    expect(contextApiMocks.queryKnowledgeBase).toHaveBeenCalledWith(
      "kb-primary",
      { query_text: "How does retrieval work?", top_k: 5 },
      "token",
    );
  });

  it("shows the upload page in read-only mode for admins", async () => {
    await renderContextWorkspace("/control/context/kb-primary/upload");

    expect(await screen.findByRole("heading", { name: "Upload documents" })).toBeVisible();
    expect(screen.getByText(/only superadmins can create, edit, upload, or delete/i)).toBeVisible();
    expect(screen.getByText("Manual Note")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Add document" })).not.toBeInTheDocument();
  });

  it("lets superadmins edit manual documents from the upload page", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload");

    expect(await screen.findByRole("heading", { name: "Upload documents" })).toBeVisible();
    expect(screen.getByText("Manual Note")).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(1);

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByDisplayValue("Manual Note")).toBeVisible();
    expect(screen.getByDisplayValue("Operator note")).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(1);
  });

  it("renders the browse documents page as summary cards with open-text links", async () => {
    await renderContextWorkspace("/control/context/kb-primary/documents");

    expect(await screen.findByRole("heading", { name: "Browse documents" })).toBeVisible();
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText("Manual Note")).toBeVisible();

    const openLinks = screen.getAllByRole("link", { name: "Open text" });
    expect(openLinks).toHaveLength(2);
    expect(openLinks[0]).toHaveAttribute("target", "_blank");
    expect(openLinks[0]).toHaveAttribute("href", "/control/context/kb-primary/documents/doc-1/view");
  });

  it("renders the document viewer with full text and handles missing documents", async () => {
    await renderContextWorkspace("/control/context/kb-primary/documents/doc-2/view");

    expect(await screen.findByRole("heading", { name: "Manual Note" })).toBeVisible();
    expect(screen.getByText("A manually curated note for testing uploads and editing.")).toBeVisible();

    await renderContextWorkspace("/control/context/kb-primary/documents/missing/view");
    expect(await screen.findByText("The requested document could not be found in this knowledge base.")).toBeVisible();
  });
});
