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
  listKnowledgeBaseSchemaProfiles: vi.fn(),
  createKnowledgeBaseSchemaProfile: vi.fn(),
}));

const WEAVIATE_PROVIDER = {
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
};

const WEAVIATE_PROFILES = [
  {
    id: "profile-rag",
    slug: "plain-document-rag",
    display_name: "Plain document RAG",
    description: "General-purpose retrieval schema.",
    provider_key: "weaviate_local",
    is_system: true,
    schema: { properties: [{ name: "title", data_type: "text" as const }] },
  },
  {
    id: "profile-semantic",
    slug: "agent-semantic-memory",
    display_name: "Agent Semantic Memory",
    description: "Structured fact memory.",
    provider_key: "weaviate_local",
    is_system: true,
    schema: { properties: [{ name: "subject", data_type: "text" as const }] },
  },
  {
    id: "profile-episodic",
    slug: "agent-episodic-memory",
    display_name: "Agent Episodic Memory",
    description: "Event memory.",
    provider_key: "weaviate_local",
    is_system: true,
    schema: { properties: [{ name: "episode_id", data_type: "text" as const }] },
  },
];

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
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue([
      WEAVIATE_PROVIDER,
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
    vi.mocked(contextApi.listKnowledgeBaseSchemaProfiles).mockResolvedValue(WEAVIATE_PROFILES);
  });

  it("loads vector providers, loads schema profiles, and submits the selected profile schema", async () => {
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
    expect(contextApi.listKnowledgeBaseSchemaProfiles).toHaveBeenCalledWith("weaviate_local", "token");

    await userEvent.type(screen.getByLabelText("Deployment slug"), "product-docs");
    await userEvent.type(screen.getByLabelText("Display name"), "Product Docs");
    await userEvent.type(screen.getByLabelText("Description"), "docs");
    await userEvent.selectOptions(await screen.findByLabelText("Schema profile"), "profile-rag");
    await userEvent.click(screen.getByRole("button", { name: "Create knowledge base" }));

    await waitFor(() => {
      expect(contextApi.createKnowledgeBase).toHaveBeenCalledWith(
        expect.objectContaining({
          slug: "product-docs",
          display_name: "Product Docs",
          description: "docs",
          backing_provider_instance_id: "provider-2",
          schema: {
            properties: [{ name: "title", data_type: "text" }],
          },
        }),
        "token",
      );
    });
  });

  it("keeps the structured editor and raw JSON view in sync", async () => {
    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    await userEvent.selectOptions(await screen.findByLabelText("Schema profile"), "profile-rag");
    const propertyInput = await screen.findByDisplayValue("title");
    await userEvent.clear(propertyInput);
    await userEvent.type(propertyInput, "headline");

    await userEvent.click(screen.getByRole("button", { name: "Raw JSON" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Schema JSON")).toHaveValue(
        '{\n  "properties": [\n    {\n      "name": "headline",\n      "data_type": "text"\n    }\n  ]\n}',
      );
    });
  });

  it("saves an edited schema as a reusable profile", async () => {
    vi.mocked(contextApi.createKnowledgeBaseSchemaProfile).mockResolvedValue({
      id: "profile-custom",
      slug: "customer-memory",
      display_name: "Customer Memory",
      description: "Reusable custom memory schema.",
      provider_key: "weaviate_local",
      is_system: false,
      schema: { properties: [{ name: "headline", data_type: "text" }] },
    });

    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    await userEvent.selectOptions(await screen.findByLabelText("Schema profile"), "profile-rag");
    const propertyInput = await screen.findByDisplayValue("title");
    await userEvent.clear(propertyInput);
    await userEvent.type(propertyInput, "headline");
    await userEvent.click(screen.getByRole("button", { name: "Save as reusable profile" }));

    await userEvent.clear(screen.getByLabelText("Profile slug"));
    await userEvent.type(screen.getByLabelText("Profile slug"), "customer-memory");
    await userEvent.clear(screen.getByLabelText("Profile display name"));
    await userEvent.type(screen.getByLabelText("Profile display name"), "Customer Memory");
    await userEvent.clear(screen.getAllByLabelText("Description")[1]);
    await userEvent.type(screen.getAllByLabelText("Description")[1], "Reusable custom memory schema.");
    await userEvent.click(screen.getByRole("button", { name: "Save schema profile" }));

    await waitFor(() => {
      expect(contextApi.createKnowledgeBaseSchemaProfile).toHaveBeenCalledWith(
        {
          slug: "customer-memory",
          display_name: "Customer Memory",
          description: "Reusable custom memory schema.",
          provider_key: "weaviate_local",
          schema: {
            properties: [{ name: "headline", data_type: "text" }],
          },
        },
        "token",
      );
    });
  });
});
