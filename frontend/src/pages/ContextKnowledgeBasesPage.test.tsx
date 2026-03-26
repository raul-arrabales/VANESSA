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
      backing_provider_key: "weaviate_local",
      lifecycle_state: "active",
      sync_status: "ready",
      schema: {},
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
