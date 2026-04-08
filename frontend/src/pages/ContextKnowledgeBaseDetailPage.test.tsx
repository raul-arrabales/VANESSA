import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import { ApiError } from "../auth/authApi";
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
    retrieval: { index: "kb_product_docs", result_count: 2, top_k: 5 },
    results: [
      {
        id: "doc-1",
        title: "Architecture Overview",
        text:
          "Retrieved chunk previews show only the first tokens until the operator expands the card to inspect the full passage and its supporting metadata tail-marker-alpha",
        uri: "https://example.com/overview",
        source_type: "manual",
        metadata: {
          document_id: "doc-1",
          chunk_index: 0,
          source_name: "Docs folder",
          uri: "https://example.com/overview",
          empty_field: "",
          unset_field: null,
        },
        chunk_length_tokens: 42,
        similarity: 0.742,
      },
      {
        id: "doc-2",
        title: "FAQ",
        text:
          "Top matches should appear first so reviewers can quickly inspect the most relevant chunk before opening lower-ranked context entries tail-marker-beta",
        uri: null,
        source_type: "local_directory",
        metadata: {
          document_id: "doc-2",
          chunk_index: 1,
          source_name: "FAQ folder",
          empty_field: "",
          unset_field: undefined,
        },
        chunk_length_tokens: 21,
        similarity: 0.913,
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

    const providerCard = screen.getByText("Backing provider").closest("article");
    expect(providerCard).not.toBeNull();
    expect(within(providerCard as HTMLElement).getByText("Weaviate local")).toBeVisible();
    expect(within(providerCard as HTMLElement).getByText("weaviate_local")).toBeVisible();

    const embeddingProviderCard = screen.getByText("Embeddings provider").closest("article");
    expect(embeddingProviderCard).not.toBeNull();
    expect(within(embeddingProviderCard as HTMLElement).getByText("Embeddings local")).toBeVisible();

    const embeddingModelCard = screen.getByText("Embeddings model").closest("article");
    expect(embeddingModelCard).not.toBeNull();
    expect(within(embeddingModelCard as HTMLElement).getByText("text-embedding-3-small")).toBeVisible();

    const chunkingStrategyCard = screen.getByText("Fixed length").closest("article");
    expect(chunkingStrategyCard).not.toBeNull();
    expect(within(chunkingStrategyCard as HTMLElement).getByText("Chunking strategy")).toBeVisible();

    const chunkLengthCard = screen.getByText("300").closest("article");
    expect(chunkLengthCard).not.toBeNull();
    expect(within(chunkLengthCard as HTMLElement).getByText("Chunk length")).toBeVisible();

    const chunkOverlapCard = screen.getByText("60").closest("article");
    expect(chunkOverlapCard).not.toBeNull();
    expect(within(chunkOverlapCard as HTMLElement).getByText("Chunk overlap")).toBeVisible();

    const usageCard = screen.getByText("Deployment usage").closest("article");
    expect(usageCard).not.toBeNull();
    expect(within(usageCard as HTMLElement).getAllByRole("listitem")).toHaveLength(1);
    expect(within(usageCard as HTMLElement).getByText("Local Default")).toBeVisible();
    expect(within(usageCard as HTMLElement).getByText("local-default · vector_store")).toBeVisible();

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

  it("lets superadmins update chunking before any documents are ingested", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };
    contextApiMocks.getKnowledgeBase.mockResolvedValueOnce({
      id: "kb-empty",
      slug: "draft-kb",
      display_name: "Draft KB",
      description: "draft",
      index_name: "kb_draft_kb",
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
          chunk_length: 254,
          chunk_overlap: 60,
        },
      },
      document_count: 0,
      deployment_usage: [],
    });
    contextApiMocks.updateKnowledgeBase.mockResolvedValueOnce({
      id: "kb-empty",
      slug: "draft-kb",
      display_name: "Draft KB",
      description: "draft",
      index_name: "kb_draft_kb",
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
      last_sync_at: null,
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
          chunk_length: 200,
          chunk_overlap: 40,
        },
      },
      document_count: 0,
      deployment_usage: [],
    });

    await renderContextWorkspace("/control/context/kb-primary");

    expect(await screen.findByText(/has not ingested any documents yet/i)).toBeVisible();
    await userEvent.clear(screen.getByLabelText("Chunk length"));
    await userEvent.type(screen.getByLabelText("Chunk length"), "200");
    await userEvent.clear(screen.getByLabelText("Chunk overlap"));
    await userEvent.type(screen.getByLabelText("Chunk overlap"), "40");
    await userEvent.click(screen.getByRole("button", { name: "Save knowledge base" }));

    await waitFor(() => {
      expect(contextApiMocks.updateKnowledgeBase).toHaveBeenCalledWith(
        "kb-empty",
        expect.objectContaining({
          chunking: {
            strategy: "fixed_length",
            config: {
              unit: "tokens",
              chunk_length: 200,
              chunk_overlap: 40,
            },
          },
        }),
        "token",
      );
    });
  });

  it("renders the sources page with subviews and lets superadmins browse and sync sources", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/sources");

    expect(await screen.findByRole("heading", { name: "Sources" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Add Source" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Existing Sources" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Sync History" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Add Source" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Add source" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Existing sources" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sync history" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Browse" }));
    await userEvent.click(await screen.findByRole("button", { name: "product_docs" }));
    await userEvent.click(screen.getByRole("button", { name: "Use current directory" }));
    expect(screen.getByDisplayValue("product_docs")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Existing Sources" }));
    expect(screen.getByRole("button", { name: "Existing Sources" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Existing sources" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Add source" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    await waitFor(() => expect(contextApiMocks.syncKnowledgeSource).toHaveBeenCalledWith("kb-primary", "source-1", "token"));
  });

  it("supports URL-driven source subviews and edit handoff", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/sources?view=history");

    expect(await screen.findByRole("heading", { name: "Sync history" })).toBeVisible();
    expect(screen.getByText(/Scanned 1 file/)).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Add source" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Existing sources" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Existing Sources" }));
    expect(await screen.findByRole("heading", { name: "Existing sources" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(await screen.findByRole("heading", { name: "Edit source" })).toBeVisible();
    expect(screen.getByDisplayValue("Docs folder")).toBeVisible();
    expect(screen.getByDisplayValue("product_docs")).toBeVisible();

  });

  it("falls back to the add-source subview for invalid superadmin source views", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/sources?view=unknown");

    expect(await screen.findByRole("heading", { name: "Add source" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Sync history" })).not.toBeInTheDocument();
  });

  it("shows the backend sync failure message when source sync is rejected", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };
    contextApiMocks.syncKnowledgeSource.mockRejectedValueOnce(
      new ApiError(
        "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens for embeddings model sentence-transformers/all-MiniLM-L6-v2 (model limit 256 including 2 special tokens). Update KB chunking to 254 or smaller and retry.",
        409,
        "knowledge_base_chunking_exceeds_embeddings_limit",
        { safe_chunk_length_max: 254 },
      ),
    );

    await renderContextWorkspace("/control/context/kb-primary/sources");

    await screen.findByRole("heading", { name: "Sources" });
    await userEvent.click(screen.getByRole("button", { name: "Existing Sources" }));
    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));

    expect(await screen.findByText(/chunk length 300 exceeds the safe maximum 254 tokens/i)).toBeVisible();
  });

  it("defaults non-superadmins to the existing sources view", async () => {
    await renderContextWorkspace("/control/context/kb-primary/sources");

    expect(await screen.findByRole("heading", { name: "Sources" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Add Source" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Existing Sources" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Sync History" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Existing sources" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Add source" })).not.toBeInTheDocument();
  });

  it("renders the retrieval page and runs retrieval queries", async () => {
    await renderContextWorkspace("/control/context/kb-primary/retrieval");

    expect(await screen.findByRole("heading", { name: "Test retrieval" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    const resultButtons = await screen.findAllByRole("button", { name: /Expand retrieval result for/i });
    expect(resultButtons).toHaveLength(2);
    expect(within(resultButtons[0] as HTMLElement).getByRole("heading", { name: "FAQ" })).toBeVisible();
    expect(within(resultButtons[1] as HTMLElement).getByRole("heading", { name: "Architecture Overview" })).toBeVisible();
    expect(within(resultButtons[0] as HTMLElement).getByText("Similarity: 0.913")).toBeVisible();
    expect(within(resultButtons[1] as HTMLElement).getByText("Similarity: 0.742")).toBeVisible();
    expect(screen.queryByText("Chunk metadata")).not.toBeInTheDocument();
    expect(screen.queryByText("Chunk length: 42 tokens")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/tail-marker-alpha/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Expand retrieval result for FAQ" }));

    expect(screen.getByLabelText("Chunk text")).toHaveDisplayValue(
      "Top matches should appear first so reviewers can quickly inspect the most relevant chunk before opening lower-ranked context entries tail-marker-beta",
    );
    expect(screen.getByText("Chunk length: 21 tokens")).toBeVisible();
    expect(screen.getByText("Chunk metadata")).toBeVisible();
    expect(screen.getByText("document_id: doc-2")).toBeVisible();
    expect(screen.getByText("chunk_index: 1")).toBeVisible();
    expect(screen.getByText("source_name: FAQ folder")).toBeVisible();
    expect(screen.queryByText(/^empty_field:/)).toBeNull();
    expect(screen.queryByText(/^unset_field:/)).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Expand retrieval result for Architecture Overview" }));

    expect(screen.getByLabelText("Chunk text")).toHaveDisplayValue(
      "Retrieved chunk previews show only the first tokens until the operator expands the card to inspect the full passage and its supporting metadata tail-marker-alpha",
    );
    expect(screen.getByText("Chunk length: 42 tokens")).toBeVisible();
    expect(screen.getByText("document_id: doc-1")).toBeVisible();
    expect(screen.getByText("chunk_index: 0")).toBeVisible();
    expect(screen.getByText("source_name: Docs folder")).toBeVisible();
    expect(screen.queryByText("source_name: FAQ folder")).not.toBeInTheDocument();
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
