import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import type { AuthUser } from "../../../auth/types";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

let mockUser: AuthUser | null = null;

vi.mock("../../../auth/AuthProvider", () => ({
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
    document_count: 2,
    deployment_usage: [],
  })),
  listKnowledgeBaseDocuments: vi.fn(async () => [
    {
      id: "doc-1",
      knowledge_base_id: "kb-primary",
      title: "Architecture Overview",
      source_type: "manual",
      source_name: "Operator note",
      uri: null,
      text: "Hello world",
      metadata: {},
      chunk_count: 1,
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
      exclude_globs: [],
      lifecycle_state: "active",
      last_sync_status: "ready",
    },
  ]),
  listKnowledgeSyncRuns: vi.fn(async () => [
    {
      id: "run-1",
      knowledge_base_id: "kb-primary",
      status: "ready",
      scanned_file_count: 1,
      changed_file_count: 1,
      deleted_file_count: 0,
      created_document_count: 1,
      updated_document_count: 0,
      deleted_document_count: 0,
    },
  ]),
}));

vi.mock("../../../api/context", () => contextApiMocks);

function LoaderHarness({
  loadDocuments = false,
  loadSources = false,
  loadSyncRuns = false,
}: {
  loadDocuments?: boolean;
  loadSources?: boolean;
  loadSyncRuns?: boolean;
}): JSX.Element {
  const detail = useContextKnowledgeBaseLoader({ loadDocuments, loadSources, loadSyncRuns });

  return (
    <section>
      <p>{detail.loading ? "loading" : "ready"}</p>
      <p>{detail.knowledgeBase?.id ?? "no-kb"}</p>
      <p>{`documents:${detail.documents.length}`}</p>
      <p>{`sources:${detail.sources.length}`}</p>
      <p>{`syncRuns:${detail.syncRuns.length}`}</p>
    </section>
  );
}

describe("useContextKnowledgeBaseLoader", () => {
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

  it("loads only the knowledge base when no optional resource flags are enabled", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/context/:knowledgeBaseId" element={<LoaderHarness />} />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    expect(await screen.findByText("ready")).toBeVisible();
    expect(screen.getByText("kb-primary")).toBeVisible();
    expect(screen.getByText("documents:0")).toBeVisible();
    expect(screen.getByText("sources:0")).toBeVisible();
    expect(screen.getByText("syncRuns:0")).toBeVisible();
    expect(contextApiMocks.getKnowledgeBase).toHaveBeenCalledWith("kb-primary", "token");
    expect(contextApiMocks.listKnowledgeBaseDocuments).not.toHaveBeenCalled();
    expect(contextApiMocks.listKnowledgeSources).not.toHaveBeenCalled();
    expect(contextApiMocks.listKnowledgeSyncRuns).not.toHaveBeenCalled();
  });

  it("loads only the explicitly requested optional resources", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route
          path="/control/context/:knowledgeBaseId"
          element={<LoaderHarness loadDocuments loadSources />}
        />
      </Routes>,
      { route: "/control/context/kb-primary" },
    );

    expect(await screen.findByText("ready")).toBeVisible();
    expect(screen.getByText("documents:1")).toBeVisible();
    expect(screen.getByText("sources:1")).toBeVisible();
    expect(screen.getByText("syncRuns:0")).toBeVisible();
    expect(contextApiMocks.listKnowledgeBaseDocuments).toHaveBeenCalledWith("kb-primary", "token");
    expect(contextApiMocks.listKnowledgeSources).toHaveBeenCalledWith("kb-primary", "token");
    expect(contextApiMocks.listKnowledgeSyncRuns).not.toHaveBeenCalled();
  });
});
