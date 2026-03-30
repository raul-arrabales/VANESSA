import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import type { AuthUser } from "../auth/types";
import ContextKnowledgeBaseCreatePage from "./ContextKnowledgeBaseCreatePage";
import * as contextApi from "../api/context";
import * as platformApi from "../api/platform";

let mockUser: AuthUser | null = null;
const navigateMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../api/platform", () => ({
  listPlatformProviders: vi.fn(),
}));

vi.mock("../api/context", () => ({
  createKnowledgeBase: vi.fn(),
}));

describe("ContextKnowledgeBaseCreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
  });

  it("loads vector providers, preselects the only option, and submits backing_provider_instance_id", async () => {
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue([
      {
        id: "provider-2",
        slug: "weaviate-local",
        provider_key: "weaviate_local",
        capability: "vector_store",
        adapter_kind: "weaviate_http",
        display_name: "Weaviate local",
        description: "Primary vector endpoint.",
        endpoint_url: "http://weaviate:8080",
        healthcheck_url: "http://weaviate:8080/v1/.well-known/ready",
        enabled: true,
        config: {},
        secret_refs: {},
      },
      {
        id: "provider-1",
        slug: "vllm-local-gateway",
        provider_key: "vllm_local",
        capability: "llm_inference",
        adapter_kind: "openai_compatible_llm",
        display_name: "vLLM local gateway",
        description: "Primary llm endpoint.",
        endpoint_url: "http://llm:8000",
        healthcheck_url: "http://llm:8000/health",
        enabled: true,
        config: {},
        secret_refs: {},
      },
    ]);
    vi.mocked(contextApi.createKnowledgeBase).mockResolvedValue({
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
      document_count: 0,
    });

    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    const providerSelect = await screen.findByLabelText("Backing provider");
    await waitFor(() => expect(providerSelect).toHaveValue("provider-2"));

    await userEvent.type(screen.getByLabelText("Deployment slug"), "product-docs");
    await userEvent.type(screen.getByLabelText("Display name"), "Product Docs");
    await userEvent.type(screen.getByLabelText("Description"), "docs");
    await userEvent.click(screen.getByRole("button", { name: "Create knowledge base" }));

    await waitFor(() => {
      expect(contextApi.createKnowledgeBase).toHaveBeenCalledWith(
        expect.objectContaining({
          slug: "product-docs",
          display_name: "Product Docs",
          description: "docs",
          backing_provider_instance_id: "provider-2",
        }),
        "token",
      );
    });
  });
});
