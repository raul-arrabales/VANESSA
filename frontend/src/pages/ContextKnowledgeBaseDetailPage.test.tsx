import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import { ApiError } from "../auth/authApi";
import type { KnowledgeBaseQueryPreprocessing, KnowledgeSource } from "../api/context";
import ContextKnowledgeBaseDetailPage from "./ContextKnowledgeBaseDetailPage";
import ContextKnowledgeBasesPage from "../features/context-management/pages/ContextKnowledgeBasesPage";
import ContextKnowledgeBaseSourcesPage from "../features/context-management/pages/ContextKnowledgeBaseSourcesPage";
import ContextKnowledgeBaseRetrievalPage from "../features/context-management/pages/ContextKnowledgeBaseRetrievalPage";
import ContextKnowledgeBaseUploadPage from "../features/context-management/pages/ContextKnowledgeBaseUploadPage";
import ContextKnowledgeBaseDocumentsPage from "../features/context-management/pages/ContextKnowledgeBaseDocumentsPage";
import ContextKnowledgeBaseDocumentViewPage from "../features/context-management/pages/ContextKnowledgeBaseDocumentViewPage";
import {
  buildKnowledgeBaseQueryResponse,
  buildKnowledgeBaseQueryResult,
} from "../features/context-management/retrievalTestBuilders";

let mockUser: AuthUser | null = null;
const scrollIntoViewMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

const contextApiMocks = vi.hoisted(() => ({
  listKnowledgeBases: vi.fn(async () => [
    {
      id: "kb-primary",
      slug: "product-docs",
      display_name: "Product Docs",
      description: "docs",
      index_name: "kb_product_docs",
      lifecycle_state: "active",
      sync_status: "ready",
      document_count: 2,
      eligible_for_binding: true,
      binding_count: 1,
    },
  ]),
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
    schema: {
      properties: [
        { name: "category", data_type: "text" },
        { name: "page_count", data_type: "int" },
        { name: "published", data_type: "boolean" },
      ],
    },
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
      metadata: {
        category: "guide",
        published: true,
        source_path: "product_docs/overview.txt",
      },
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
      metadata: {
        category: "memo",
        page_count: 2,
      },
      chunk_count: 2,
      source_id: null,
      source_path: null,
      source_document_key: null,
      managed_by_source: false,
    },
  ]),
  listKnowledgeSources: vi.fn<() => Promise<KnowledgeSource[]>>(async () => [
    {
      id: "source-1",
      knowledge_base_id: "kb-primary",
      source_type: "local_directory",
      display_name: "Docs folder",
      relative_path: "product_docs",
      include_globs: ["**/*.md"],
      exclude_globs: [] as string[],
      metadata: {
        category: "guide",
        published: true,
      },
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
  queryKnowledgeBase: vi.fn(
    async (
      _knowledgeBaseId: string,
      payload?: { search_method?: string; query_preprocessing?: KnowledgeBaseQueryPreprocessing; hybrid_alpha?: number },
    ) => {
    if (payload?.search_method === "hybrid") {
      return buildKnowledgeBaseQueryResponse({
        searchMethod: "hybrid",
        queryPreprocessing: payload.query_preprocessing ?? "none",
        hybridAlpha: payload.hybrid_alpha ?? 0.5,
        results: [
          buildKnowledgeBaseQueryResult({
            id: "doc-2",
            title: "FAQ",
            text:
              "Hybrid retrieval blends semantic recall with lexical precision so testers can inspect high-confidence overlap results first tail-marker-hybrid-beta",
            uri: null,
            source_type: "local_directory",
            metadata: {
              document_id: "doc-2",
              chunk_index: 1,
              source_name: "FAQ folder",
            },
            chunk_length_tokens: 18,
            relevance_score: 0.875,
            relevance_kind: "hybrid_score",
            relevance_components: {
              semantic_score: 0.75,
              keyword_score: 1,
            },
          }),
          buildKnowledgeBaseQueryResult({
            id: "doc-1",
            title: "Architecture Overview",
            text:
              "Hybrid fusion keeps strong semantic-only matches available even when lexical overlap is weaker tail-marker-hybrid-alpha",
            uri: "https://example.com/overview",
            metadata: {
              document_id: "doc-1",
              chunk_index: 0,
              source_name: "Docs folder",
              uri: "https://example.com/overview",
            },
            chunk_length_tokens: 15,
            relevance_score: 0.625,
            relevance_kind: "hybrid_score",
            relevance_components: {
              semantic_score: 0.9,
              keyword_score: 0.35,
            },
          }),
        ],
      });
    }
    if (payload?.search_method === "keyword") {
      return buildKnowledgeBaseQueryResponse({
        searchMethod: "keyword",
        queryPreprocessing: payload.query_preprocessing ?? "none",
        results: [
          buildKnowledgeBaseQueryResult({
            id: "doc-1",
            text:
              "Keyword retrieval can surface exact term matches for operators who want to inspect lexical hits first tail-marker-keyword-alpha",
            uri: "https://example.com/overview",
            metadata: {
              document_id: "doc-1",
              chunk_index: 0,
              source_name: "Docs folder",
              uri: "https://example.com/overview",
              empty_field: "",
              unset_field: null,
            },
            chunk_length_tokens: 19,
            relevance_score: 4.125,
            relevance_kind: "keyword_score",
          }),
          buildKnowledgeBaseQueryResult({
            id: "doc-2",
            title: "FAQ",
            text:
              "Keyword ranking may differ from semantic ranking because provider text scoring favors term overlap tail-marker-keyword-beta",
            uri: null,
            source_type: "local_directory",
            metadata: {
              document_id: "doc-2",
              chunk_index: 1,
              source_name: "FAQ folder",
              empty_field: "",
              unset_field: undefined,
            },
            chunk_length_tokens: 16,
            relevance_score: 2.5,
            relevance_kind: "keyword_score",
          }),
        ],
      });
    }
    return buildKnowledgeBaseQueryResponse({
      searchMethod: "semantic",
      queryPreprocessing: payload?.query_preprocessing ?? "none",
      results: [
        buildKnowledgeBaseQueryResult({
          id: "doc-1",
          text:
            "Retrieved chunk previews show only the first tokens until the operator expands the card to inspect the full passage and its supporting metadata tail-marker-alpha",
          uri: "https://example.com/overview",
          metadata: {
            document_id: "doc-1",
            chunk_index: 0,
            source_name: "Docs folder",
            uri: "https://example.com/overview",
            empty_field: "",
            unset_field: null,
          },
          chunk_length_tokens: 42,
          relevance_score: 0.742,
          relevance_kind: "similarity",
        }),
        buildKnowledgeBaseQueryResult({
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
          relevance_score: 0.913,
          relevance_kind: "similarity",
        }),
      ],
    });
  }),
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
    schema: {
      properties: [
        { name: "category", data_type: "text" },
        { name: "page_count", data_type: "int" },
        { name: "published", data_type: "boolean" },
      ],
    },
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
      schema: {
        properties: [
          { name: "category", data_type: "text" },
          { name: "page_count", data_type: "int" },
          { name: "published", data_type: "boolean" },
        ],
      },
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
      metadata: {
        category: "guide",
        published: true,
      },
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

async function renderContextWorkspace(route: string) {
  return await renderWithAppProviders(
    <Routes>
      <Route path="/control/context" element={<ContextKnowledgeBasesPage />} />
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
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoViewMock,
    });
    scrollIntoViewMock.mockReset();
    mockUser = {
      id: 1,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };
  });

  it("renders the overview page with metadata and workspace subnav", async () => {
    contextApiMocks.listKnowledgeSources.mockResolvedValueOnce([
      {
        id: "source-1",
        knowledge_base_id: "kb-primary",
        source_type: "local_directory",
        display_name: "Docs folder",
        relative_path: "product_docs",
        include_globs: ["**/*.md"],
        exclude_globs: [] as string[],
        metadata: {
          category: "guide",
          published: true,
        },
        lifecycle_state: "active",
        last_sync_status: "ready",
        last_sync_at: "2026-03-26T20:10:00+00:00",
        last_sync_error: null,
      },
      {
        id: "source-2",
        knowledge_base_id: "kb-primary",
        source_type: "local_directory",
        display_name: "Draft folder",
        relative_path: "draft_docs",
        include_globs: ["**/*.md"],
        exclude_globs: [] as string[],
        metadata: {
          category: "draft",
        },
        lifecycle_state: "active",
        last_sync_status: "error",
        last_sync_at: "2026-03-26T20:12:00+00:00",
        last_sync_error: "Source sync failed.",
      },
    ]);

    const view = await renderContextWorkspace("/control/context/kb-primary");

    expect(await screen.findByRole("heading", { name: "Product Docs" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Overview" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Manage Sources" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Upload Documents" })).toBeVisible();

    const summaryCards = Array.from(view.container.querySelectorAll(".context-kb-summary-card"));
    expect(summaryCards.length).toBeGreaterThan(4);
    expect(within(summaryCards[0] as HTMLElement).getByText("Knowledge base")).toBeVisible();
    expect(within(summaryCards[0] as HTMLElement).getByText("Product Docs")).toBeVisible();

    const indexedFilesCard = summaryCards.find((card) => within(card as HTMLElement).queryByText("Indexed files"));
    expect(indexedFilesCard).not.toBeNull();
    expect(within(indexedFilesCard as HTMLElement).getByText("2")).toBeVisible();

    const sourcesCard = summaryCards.find((card) => within(card as HTMLElement).queryByText(/^Sources$/));
    expect(sourcesCard).not.toBeNull();
    expect(within(sourcesCard as HTMLElement).getByText("2")).toBeVisible();

    const syncedSourcesCard = summaryCards.find((card) => within(card as HTMLElement).queryByText("Synced sources"));
    expect(syncedSourcesCard).not.toBeNull();
    expect(within(syncedSourcesCard as HTMLElement).getByText("1")).toBeVisible();

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
      schema: {
        properties: [
          { name: "category", data_type: "text" },
          { name: "page_count", data_type: "int" },
          { name: "published", data_type: "boolean" },
        ],
      },
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
      schema: {
        properties: [
          { name: "category", data_type: "text" },
          { name: "page_count", data_type: "int" },
          { name: "published", data_type: "boolean" },
        ],
      },
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

  it("opens a confirmation dialog before deleting a knowledge base", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary");

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Delete knowledge base" }));

    expect(screen.getByRole("dialog", { name: "Delete knowledge base" })).toBeVisible();
    expect(screen.getByText("Delete 'Product Docs'? This action cannot be undone.")).toBeVisible();
    expect(contextApiMocks.deleteKnowledgeBase).not.toHaveBeenCalled();
  });

  it("closes the delete confirmation dialog without deleting when canceled", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary");

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Delete knowledge base" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog", { name: "Delete knowledge base" })).not.toBeInTheDocument();
    expect(contextApiMocks.deleteKnowledgeBase).not.toHaveBeenCalled();
  });

  it("deletes the knowledge base only after confirmation and shows success feedback on redirect", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };
    contextApiMocks.deleteKnowledgeBase.mockResolvedValueOnce(undefined);

    await renderContextWorkspace("/control/context/kb-primary");

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Delete knowledge base" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm delete" }));

    await waitFor(() => expect(contextApiMocks.deleteKnowledgeBase).toHaveBeenCalledWith("kb-primary", "token"));
    expect(await screen.findByRole("heading", { name: "Context management" })).toBeVisible();
    expect(await screen.findByText("Knowledge base 'Product Docs' deleted.")).toBeVisible();
  });

  it("keeps the delete dialog open and non-dismissible while deletion is pending", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };
    let resolveDelete!: () => void;
    contextApiMocks.deleteKnowledgeBase.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveDelete = resolve;
        }),
    );

    await renderContextWorkspace("/control/context/kb-primary");

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Delete knowledge base" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm delete" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Confirm delete" })).toBeDisabled();
    });

    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Delete knowledge base" })).toBeVisible();

    expect(resolveDelete).toBeTypeOf("function");
    resolveDelete();
    await waitFor(() => expect(contextApiMocks.deleteKnowledgeBase).toHaveBeenCalledWith("kb-primary", "token"));
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
    expect(screen.getByText("Enter a relative path manually or click Browse to choose a directory.")).toBeVisible();

    const browseButton = screen.getByRole("button", { name: "Browse" });
    const relativePathLabel = screen.getByText("Relative path");
    expect(browseButton.compareDocumentPosition(relativePathLabel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await userEvent.click(browseButton);
    const usedDirectoryButton = await screen.findByRole("button", { name: "product_docs (Used)" });
    expect(usedDirectoryButton).toBeDisabled();
    expect(screen.getByRole("button", { name: "Use current directory" })).toBeDisabled();
    expect(screen.getByRole("heading", { name: "Browse source directories" }).closest(".panel-nested")).toBeTruthy();

    const relativePathInput = document.getElementById("kb-source-relative-path");
    expect(relativePathInput).toBeInstanceOf(HTMLInputElement);
    await userEvent.type(relativePathInput as HTMLInputElement, "product_docs");
    await userEvent.click(screen.getByRole("button", { name: "Add source" }));
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("This directory is already configured for another source.")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Existing Sources" }));
    expect(screen.getByRole("button", { name: "Existing Sources" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Existing sources" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Add source" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Docs folder" }).closest(".panel-nested")).toBeTruthy();

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
    expect(screen.getByRole("heading", { name: "Docs folder" }).closest(".panel-nested")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Add source" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Existing sources" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Existing Sources" }));
    expect(await screen.findByRole("heading", { name: "Existing sources" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(await screen.findByRole("heading", { name: "Edit source" })).toBeVisible();
    expect(screen.getByDisplayValue("Docs folder")).toBeVisible();
    expect(screen.getByDisplayValue("product_docs")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Browse" }));
    expect(await screen.findByRole("button", { name: "Use current directory" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "product_docs/guides" })).toBeEnabled();

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
    expect(screen.getByRole("heading", { name: "Retrieval settings" })).toBeVisible();
    expect(screen.getByLabelText("Search method")).toHaveValue("semantic");
    expect(screen.getByLabelText("Query preprocessing")).toHaveValue("none");
    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");
    let nowCallCount = 0;
    const performanceNowSpy = vi.spyOn(performance, "now").mockImplementation(() => {
      nowCallCount += 1;
      return nowCallCount === 1 ? 100 : 460;
    });
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    const resultButtons = await screen.findAllByRole("button", { name: /Expand retrieval result for/i });
    expect(resultButtons).toHaveLength(2);
    expect(screen.getByText("2 retrieval result(s)")).toBeVisible();
    expect(screen.getByText("Completed in 360 ms.")).toBeVisible();
    expect(scrollIntoViewMock).toHaveBeenCalledWith({
      behavior: "smooth",
      block: "start",
    });
    expect(within(resultButtons[0] as HTMLElement).getByRole("heading", { name: "Chunk 1: FAQ" })).toBeVisible();
    expect(within(resultButtons[1] as HTMLElement).getByRole("heading", { name: "Chunk 2: Architecture Overview" })).toBeVisible();
    expect(within(resultButtons[0] as HTMLElement).getByText("Similarity: 0.913")).toBeVisible();
    expect(within(resultButtons[1] as HTMLElement).getByText("Similarity: 0.742")).toBeVisible();
    expect((resultButtons[0] as HTMLElement).querySelector(".context-retrieval-result-expand-indicator")).not.toBeNull();
    expect(screen.queryByText("Chunk metadata")).not.toBeInTheDocument();
    expect(screen.queryByText("Chunk length: 42 tokens")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(/tail-marker-alpha/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Expand retrieval result for Chunk 1: FAQ" }));

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

    await userEvent.click(screen.getByRole("button", { name: "Expand retrieval result for Chunk 2: Architecture Overview" }));

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
      {
        query_text: "How does retrieval work?",
        top_k: 5,
        search_method: "semantic",
        query_preprocessing: "none",
      },
      "token",
    );
    performanceNowSpy.mockRestore();
  });

  it("keeps the last successful retrieval snapshot visible after a failed rerun", async () => {
    contextApiMocks.queryKnowledgeBase
      .mockResolvedValueOnce(
        buildKnowledgeBaseQueryResponse({
          results: [
            buildKnowledgeBaseQueryResult({
              id: "doc-stable",
              title: "Stable Result",
              text: "This result should remain visible after a failed rerun tail-marker-stable",
              metadata: {
                document_id: "doc-stable",
                chunk_index: 0,
                source_name: "Stable source",
              },
              chunk_length_tokens: 11,
              relevance_score: 0.81,
            }),
          ],
        }),
      )
      .mockRejectedValueOnce(new ApiError("Retrieval request failed.", 500, "retrieval_failed"));

    await renderContextWorkspace("/control/context/kb-primary/retrieval");

    expect(await screen.findByRole("heading", { name: "Test retrieval" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");

    let nowCallCount = 0;
    const performanceNowSpy = vi.spyOn(performance, "now").mockImplementation(() => {
      nowCallCount += 1;
      return nowCallCount === 1 ? 100 : 460;
    });

    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    expect(await screen.findByText("1 retrieval result(s)")).toBeVisible();
    expect(screen.getByText("Completed in 360 ms.")).toBeVisible();
    expect(await screen.findByRole("button", { name: "Expand retrieval result for Chunk 1: Stable Result" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("Retrieval request failed.")).toBeVisible();
    expect(screen.getByText("1 retrieval result(s)")).toBeVisible();
    expect(screen.getByText("Completed in 360 ms.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Expand retrieval result for Chunk 1: Stable Result" })).toBeVisible();

    performanceNowSpy.mockRestore();
  });

  it("lets the operator switch retrieval search method to keyword", async () => {
    await renderContextWorkspace("/control/context/kb-primary/retrieval");

    expect(await screen.findByRole("heading", { name: "Test retrieval" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");
    await userEvent.selectOptions(screen.getByLabelText("Search method"), "keyword");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    const resultButtons = await screen.findAllByRole("button", { name: /Expand retrieval result for/i });
    expect(within(resultButtons[0] as HTMLElement).getByRole("heading", { name: "Chunk 1: Architecture Overview" })).toBeVisible();
    expect(within(resultButtons[0] as HTMLElement).getByText("Keyword score: 4.125")).toBeVisible();
    expect(within(resultButtons[1] as HTMLElement).getByText("Keyword score: 2.500")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Expand retrieval result for Chunk 1: Architecture Overview" }));

    expect(screen.getByLabelText("Chunk text")).toHaveDisplayValue(
      "Keyword retrieval can surface exact term matches for operators who want to inspect lexical hits first tail-marker-keyword-alpha",
    );
    expect(screen.getByText("Chunk length: 19 tokens")).toBeVisible();
    expect(screen.getByText("document_id: doc-1")).toBeVisible();
    expect(contextApiMocks.queryKnowledgeBase).toHaveBeenCalledWith(
      "kb-primary",
      {
        query_text: "How does retrieval work?",
        top_k: 5,
        search_method: "keyword",
        query_preprocessing: "none",
      },
      "token",
    );
  });

  it("lets the operator run hybrid retrieval with a configurable alpha", async () => {
    await renderContextWorkspace("/control/context/kb-primary/retrieval");

    expect(await screen.findByRole("heading", { name: "Test retrieval" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Retrieval query"), "How does retrieval work?");
    await userEvent.selectOptions(screen.getByLabelText("Search method"), "hybrid");

    const hybridAlphaInput = screen.getByLabelText("Hybrid alpha");
    expect(hybridAlphaInput).toHaveValue(0.5);

    await userEvent.clear(hybridAlphaInput);
    await userEvent.type(hybridAlphaInput, "0.65");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    const resultButtons = await screen.findAllByRole("button", { name: /Expand retrieval result for/i });
    expect(within(resultButtons[0] as HTMLElement).getByRole("heading", { name: "Chunk 1: FAQ" })).toBeVisible();
    expect(within(resultButtons[0] as HTMLElement).getByText("Hybrid score: 0.875")).toBeVisible();
    expect(within(resultButtons[1] as HTMLElement).getByText("Hybrid score: 0.625")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Expand retrieval result for Chunk 1: FAQ" }));

    expect(screen.getByLabelText("Chunk text")).toHaveDisplayValue(
      "Hybrid retrieval blends semantic recall with lexical precision so testers can inspect high-confidence overlap results first tail-marker-hybrid-beta",
    );
    expect(screen.getByText("Chunk length: 18 tokens")).toBeVisible();
    expect(screen.getByText("Semantic score: 0.750")).toBeVisible();
    expect(screen.getByText("Keyword score: 1.000")).toBeVisible();
    expect(contextApiMocks.queryKnowledgeBase).toHaveBeenCalledWith(
      "kb-primary",
      {
        query_text: "How does retrieval work?",
        top_k: 5,
        search_method: "hybrid",
        query_preprocessing: "none",
        hybrid_alpha: 0.65,
      },
      "token",
    );
  });

  it("lets the operator enable query preprocessing before retrieval", async () => {
    await renderContextWorkspace("/control/context/kb-primary/retrieval");

    expect(await screen.findByRole("heading", { name: "Test retrieval" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Retrieval query"), "Raúl!!!");
    await userEvent.selectOptions(screen.getByLabelText("Query preprocessing"), "normalize");
    await userEvent.click(screen.getByRole("button", { name: "Test retrieval" }));

    expect(contextApiMocks.queryKnowledgeBase).toHaveBeenCalledWith(
      "kb-primary",
      {
        query_text: "Raúl!!!",
        top_k: 5,
        search_method: "semantic",
        query_preprocessing: "normalize",
      },
      "token",
    );
  });

  it("shows the upload page in read-only mode for admins", async () => {
    await renderContextWorkspace("/control/context/kb-primary/upload?view=manual");

    expect(await screen.findByRole("heading", { name: "Upload documents" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Manage Manual Documents" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Manual Document" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload Files" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Manage manual documents" })).toBeVisible();
    expect(screen.getByText(/only superadmins can create, edit, upload, or delete/i)).toBeVisible();
    expect(screen.getByText("Manual Note")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Add document" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Upload files")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Document title")).not.toBeInTheDocument();
  });

  it("shows all upload subviews for superadmins and defaults to the manual document form", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload");

    expect(await screen.findByRole("heading", { name: "Upload documents" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Manual Document" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Upload Files" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Manage Manual Documents" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Manual document" })).toBeVisible();
    expect(screen.getByLabelText("Document title")).toBeVisible();
    expect(screen.getByLabelText("Document text")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Metadata" })).toBeVisible();
    expect(screen.queryByLabelText("Upload files")).not.toBeInTheDocument();
    expect(screen.queryByText("Manual Note")).not.toBeInTheDocument();
  });

  it("supports the upload subview deep link for superadmins", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload?view=upload");

    expect(await screen.findByRole("heading", { name: "Upload supported files" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Upload Files" })).toHaveAttribute("aria-pressed", "true");
    expect(document.querySelector('input[type="file"]')).not.toBeNull();
    expect(screen.getByText("Supported file types: .txt, .md, .json, .jsonl, .pdf.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Metadata" })).toBeVisible();
    expect(screen.queryByLabelText("Document title")).not.toBeInTheDocument();
    expect(screen.queryByText("Manual Note")).not.toBeInTheDocument();
  });

  it("supports the manage subview deep link for superadmins", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload?view=manage");

    expect(await screen.findByRole("heading", { name: "Manage manual documents" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Manage Manual Documents" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Manual Note")).toBeVisible();
    expect(screen.queryByLabelText("Upload files")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Document title")).not.toBeInTheDocument();
  });

  it("falls back invalid upload subviews to the manual view for superadmins", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload?view=unknown");

    expect(await screen.findByRole("heading", { name: "Manual document" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Manual Document" })).toHaveAttribute("aria-pressed", "true");
  });

  it("lets superadmins edit manual documents from the upload manage view", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload?view=manage");

    expect(await screen.findByRole("heading", { name: "Manage manual documents" })).toBeVisible();
    expect(screen.getByText("Manual Note")).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(1);

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Manual Document" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Manual document" })).toBeVisible();
    expect(screen.getByDisplayValue("Manual Note")).toBeVisible();
    expect(screen.getByDisplayValue("Operator note")).toBeVisible();
    expect(screen.getByDisplayValue("memo")).toBeVisible();
    expect(screen.getByDisplayValue("2")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("submits manual-document metadata using schema-driven fields", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload");

    await screen.findByRole("heading", { name: "Manual document" });
    await userEvent.click(screen.getByRole("button", { name: "Add metadata property" }));
    const propertySelect = screen.getByLabelText("Property name");
    await userEvent.selectOptions(propertySelect, "category");
    await userEvent.type(screen.getByLabelText("Property value"), "guide");
    await userEvent.type(screen.getByLabelText("Document title"), "Release note");
    await userEvent.type(screen.getByLabelText("Document text"), "Document body");

    await userEvent.click(screen.getByRole("button", { name: "Add document" }));

    await waitFor(() => expect(contextApiMocks.createKnowledgeBaseDocument).toHaveBeenCalledWith(
      "kb-primary",
      expect.objectContaining({
        title: "Release note",
        text: "Document body",
        metadata: { category: "guide" },
      }),
      "token",
    ));
  });

  it("submits shared upload metadata for uploaded files", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/upload?view=upload");

    await screen.findByRole("heading", { name: "Upload supported files" });
    await userEvent.click(screen.getByRole("button", { name: "Add metadata property" }));
    await userEvent.selectOptions(screen.getByLabelText("Property name"), "published");
    await userEvent.selectOptions(screen.getByLabelText("Property value"), "true");
    const file = new File(["hello"], "guide.txt", { type: "text/plain" });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(fileInput, file);

    await userEvent.click(screen.getByRole("button", { name: "Upload files" }));

    await waitFor(() => expect(contextApiMocks.uploadKnowledgeBaseDocuments).toHaveBeenCalledWith(
      "kb-primary",
      [file],
      { published: true },
      "token",
    ));
  });

  it("renders the browse documents page as summary cards with document actions", async () => {
    await renderContextWorkspace("/control/context/kb-primary/documents");

    expect(await screen.findByRole("heading", { name: "Browse documents" })).toBeVisible();
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText("Manual Note")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Architecture Overview" }).closest(".panel-nested")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Manual Note" }).closest(".panel-nested")).toBeTruthy();

    const openLinks = screen.getAllByRole("link", { name: "Open text" });
    expect(openLinks).toHaveLength(2);
    expect(openLinks[0]).toHaveAttribute("target", "_blank");
    expect(openLinks[0]).toHaveAttribute("href", "/control/context/kb-primary/documents/doc-1/view");
    expect(screen.getAllByRole("button", { name: "View metadata" })).toHaveLength(2);
  });

  it("shows effective metadata in a modal from the browse documents page", async () => {
    await renderContextWorkspace("/control/context/kb-primary/documents");

    await screen.findByRole("heading", { name: "Browse documents" });
    await userEvent.click(screen.getAllByRole("button", { name: "View metadata" })[0]);

    expect(await screen.findByRole("dialog", { name: "Metadata for Architecture Overview" })).toBeVisible();
    expect(screen.getByText("category")).toBeVisible();
    expect(screen.getByText("guide")).toBeVisible();
    expect(screen.getByText("published")).toBeVisible();
    expect(screen.getByText("true")).toBeVisible();
    expect(screen.getByText("source_path")).toBeVisible();
    expect(screen.getByText("product_docs/overview.txt")).toBeVisible();
  });

  it("preloads source metadata when editing an existing source", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };

    await renderContextWorkspace("/control/context/kb-primary/sources?view=list");

    await screen.findByRole("heading", { name: "Existing sources" });
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(await screen.findByRole("heading", { name: "Edit source" })).toBeVisible();
    expect(screen.getByDisplayValue("guide")).toBeVisible();
    const propertyValueFields = screen.getAllByLabelText("Property value");
    expect((propertyValueFields[1] as HTMLSelectElement).value).toBe("true");
  });

  it("renders the document viewer with full text and handles missing documents", async () => {
    await renderContextWorkspace("/control/context/kb-primary/documents/doc-2/view");

    expect(await screen.findByRole("heading", { name: "Manual Note" })).toBeVisible();
    expect(screen.getByText("A manually curated note for testing uploads and editing.")).toBeVisible();

    await renderContextWorkspace("/control/context/kb-primary/documents/missing/view");
    expect(await screen.findByText("The requested document could not be found in this knowledge base.")).toBeVisible();
  });
});
