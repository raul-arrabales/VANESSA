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
    last_sync_summary: "Resynced 1 document(s) and 1 chunk(s).",
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
    expect(screen.getByText(/Weaviate local/)).toBeVisible();
    expect(screen.getByText(/Embeddings local/)).toBeVisible();
    expect(screen.getByText(/text-embedding-3-small/)).toBeVisible();
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

  it("prefills new source globs for superadmins", async () => {
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

    expect(screen.getByLabelText("Include globs")).toHaveValue("**/*.{md,txt,pdf,json,jsonl}");
    expect(screen.getByLabelText("Exclude globs")).toHaveValue("**/.git/**\n**/node_modules/**\n**/venv/**\n**/*.log");
  });

  it("keeps stored glob values when editing an existing source", async () => {
    mockUser = {
      id: 1,
      email: "superadmin@example.com",
      username: "superadmin",
      role: "superadmin",
      is_active: true,
    };
    contextApiMocks.listKnowledgeSources.mockImplementationOnce(async () => [
      {
        id: "source-1",
        knowledge_base_id: "kb-primary",
        source_type: "local_directory",
        display_name: "Docs folder",
        relative_path: "product_docs",
        include_globs: ["**/*.txt"],
        exclude_globs: ["**/*.tmp"],
        lifecycle_state: "active",
        last_sync_status: "ready",
        last_sync_at: "2026-03-26T20:10:00+00:00",
        last_sync_error: null,
      },
    ]);

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/context/:knowledgeBaseId" element={<ContextKnowledgeBaseDetailPage />} />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    await screen.findByRole("heading", { name: "Product Docs" });
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("Include globs")).toHaveValue("**/*.txt");
    expect(screen.getByLabelText("Exclude globs")).toHaveValue("**/*.tmp");
  });

  it("lets superadmins browse and select a source directory", async () => {
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
    await userEvent.click(screen.getByRole("button", { name: "Browse" }));
    await userEvent.click(await screen.findByRole("button", { name: "product_docs" }));
    await userEvent.click(screen.getByRole("button", { name: "Use current directory" }));

    expect(screen.getByDisplayValue("product_docs")).toBeVisible();
    expect(contextApiMocks.getKnowledgeSourceDirectories).toHaveBeenCalledWith("token", { rootId: null, relativePath: null });
    expect(contextApiMocks.getKnowledgeSourceDirectories).toHaveBeenCalledWith("token", {
      rootId: "root-1",
      relativePath: "product_docs",
    });
  });

  it("lets superadmins type into overview, source, and document forms without crashing", async () => {
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

    const displayNameInputs = screen.getAllByDisplayValue("Product Docs");
    await userEvent.clear(displayNameInputs[0]);
    await userEvent.type(displayNameInputs[0], "Updated KB");

    const textboxes = screen.getAllByRole("textbox");
    const relativePathInput = textboxes[4];
    await userEvent.type(relativePathInput, "product_docs");

    const includeGlobsInput = screen.getByLabelText("Include globs");
    await userEvent.clear(includeGlobsInput);
    await userEvent.type(includeGlobsInput, "**/*.md");

    const documentTitleInput = screen.getByRole("textbox", { name: "Document title" });
    await userEvent.type(documentTitleInput, "Manual note");

    expect(screen.getByDisplayValue("Updated KB")).toBeVisible();
    expect(screen.getByDisplayValue("product_docs")).toBeVisible();
    expect(screen.getByDisplayValue("**/*.md")).toBeVisible();
    expect(screen.getByDisplayValue("Manual note")).toBeVisible();
  });
});
