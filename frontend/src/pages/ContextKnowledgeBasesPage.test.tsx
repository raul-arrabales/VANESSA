import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import ContextKnowledgeBasesPage from "./ContextKnowledgeBasesPage";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("../api/context", () => ({
  listKnowledgeBases: vi.fn(async () => [
    {
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
      document_count: 3,
      binding_count: 1,
    },
  ]),
}));

describe("ContextKnowledgeBasesPage", () => {
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

  it("renders the knowledge-base inventory", async () => {
    await renderWithAppProviders(<ContextKnowledgeBasesPage />, { route: "/control/context" });

    expect(await screen.findByRole("heading", { name: "Context management" })).toBeVisible();
    expect(screen.getByText("Product Docs")).toBeVisible();
    expect(screen.getByText("kb_product_docs")).toBeVisible();
  });
});
