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
  getKnowledgeBaseVectorizationOptions: vi.fn(),
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

const VECTORIZATION_OPTIONS = {
  backing_provider: {
    id: "provider-2",
    slug: "weaviate-local",
    provider_key: "weaviate_local",
    display_name: "Weaviate local",
    enabled: true,
    capability: "vector_store",
  },
  supports_named_vectors: true,
  supported_modes: [
    { mode: "vanessa_embeddings" as const, requires_embedding_target: true },
    { mode: "self_provided" as const, requires_embedding_target: false },
  ],
  embedding_providers: [
    {
      id: "embedding-provider-1",
      slug: "embeddings-local",
      provider_key: "openai_compatible_cloud_embeddings",
      display_name: "Embeddings local",
      enabled: true,
      capability: "embeddings",
      is_ready: true,
      unavailable_reason: null,
      default_resource_id: "text-embedding-3-small",
      resources: [
        { id: "text-embedding-3-small", display_name: "text-embedding-3-small", provider_resource_id: "text-embedding-3-small" },
      ],
    },
  ],
};

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
    vi.mocked(contextApi.getKnowledgeBaseVectorizationOptions).mockResolvedValue(VECTORIZATION_OPTIONS);
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
      document_count: 0,
    });

    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    const providerSelect = await screen.findByLabelText("Backing provider");
    await waitFor(() => expect(providerSelect).toHaveValue("provider-2"));
    expect(contextApi.listKnowledgeBaseSchemaProfiles).toHaveBeenCalledWith("weaviate_local", "token");
    expect(contextApi.getKnowledgeBaseVectorizationOptions).toHaveBeenCalledWith("provider-2", "token");
    expect(screen.getByRole("heading", { name: "Advanced settings" }).closest(".panel-nested")).toBeTruthy();
    expect(await screen.findByLabelText("Chunking strategy")).toHaveValue("fixed_length");
    expect(screen.getByLabelText("Chunk length")).toHaveValue(300);
    expect(screen.getByLabelText("Chunk overlap")).toHaveValue(60);

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
          vectorization: {
            mode: "vanessa_embeddings",
            embedding_provider_instance_id: "embedding-provider-1",
            embedding_resource_id: "text-embedding-3-small",
          },
          chunking: {
            strategy: "fixed_length",
            config: {
              unit: "tokens",
              chunk_length: 300,
              chunk_overlap: 60,
            },
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

  it("shows the self-provided warning and submits self_provided mode", async () => {
    vi.mocked(contextApi.createKnowledgeBase).mockResolvedValue({
      id: "kb-self-provided",
      slug: "self-provided-kb",
      display_name: "Self Provided KB",
      description: "vectors",
      index_name: "kb_self_provided_kb",
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
        mode: "self_provided",
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
      document_count: 0,
    });

    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    await userEvent.type(screen.getByLabelText("Deployment slug"), "self-provided-kb");
    await userEvent.type(screen.getByLabelText("Display name"), "Self Provided KB");
    await userEvent.type(screen.getByLabelText("Description"), "vectors");
    await userEvent.selectOptions(await screen.findByLabelText("Schema profile"), "profile-rag");
    await userEvent.selectOptions(await screen.findByLabelText("Vectorization strategy"), "self_provided");

    expect(await screen.findByText(/text ingestion and text-query retrieval flows are not available/i)).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Create knowledge base" }));

    await waitFor(() => {
      expect(contextApi.createKnowledgeBase).toHaveBeenCalledWith(
        expect.objectContaining({
          vectorization: {
            mode: "self_provided",
          },
          chunking: {
            strategy: "fixed_length",
            config: {
              unit: "tokens",
              chunk_length: 300,
              chunk_overlap: 60,
            },
          },
        }),
        "token",
      );
    });
  });

  it("validates chunk overlap before submitting", async () => {
    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    await userEvent.type(screen.getByLabelText("Deployment slug"), "product-docs");
    await userEvent.type(screen.getByLabelText("Display name"), "Product Docs");
    await userEvent.type(screen.getByLabelText("Description"), "docs");
    await userEvent.selectOptions(await screen.findByLabelText("Schema profile"), "profile-rag");
    await userEvent.clear(screen.getByLabelText("Chunk overlap"));
    await userEvent.type(screen.getByLabelText("Chunk overlap"), "300");
    await userEvent.click(screen.getByRole("button", { name: "Create knowledge base" }));

    await waitFor(() => {
      expect(contextApi.createKnowledgeBase).not.toHaveBeenCalled();
    });
    expect(screen.getByText("Chunk overlap must be smaller than chunk length.")).toBeVisible();
  });

  it("shows a local embeddings provider with no models and explains why it cannot be selected fully yet", async () => {
    vi.mocked(contextApi.getKnowledgeBaseVectorizationOptions).mockResolvedValue({
      ...VECTORIZATION_OPTIONS,
      embedding_providers: [
        {
          id: "embedding-provider-local",
          slug: "vllm-embeddings-local",
          provider_key: "vllm_embeddings_local",
          display_name: "vLLM embeddings local",
          enabled: true,
          capability: "embeddings",
          is_ready: false,
          unavailable_reason: "no_embedding_resources",
          default_resource_id: null,
          resources: [],
        },
      ],
    });

    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    const providerSelect = await screen.findByLabelText("Embeddings provider");
    expect(screen.getByRole("option", { name: /vLLM embeddings local/i })).toBeVisible();

    await userEvent.selectOptions(providerSelect, "embedding-provider-local");

    const resourceSelect = screen.getByLabelText("Embeddings model");
    expect(resourceSelect).toBeDisabled();
    expect(
      screen.getByText(/Assign a loaded embeddings model in Platform Control before using it/i),
    ).toBeVisible();
  });

  it("auto-seeds chunk length from the selected embeddings model safe maximum and blocks larger values", async () => {
    vi.mocked(contextApi.getKnowledgeBaseVectorizationOptions).mockResolvedValue({
      ...VECTORIZATION_OPTIONS,
      embedding_providers: [
        {
          ...VECTORIZATION_OPTIONS.embedding_providers[0],
          resources: [
            {
              id: "text-embedding-3-small",
              display_name: "text-embedding-3-small",
              provider_resource_id: "text-embedding-3-small",
              chunking_constraints: {
                max_input_tokens: 256,
                special_tokens_per_input: 2,
                safe_chunk_length_max: 254,
              },
            },
          ],
        },
      ],
    });

    await renderWithAppProviders(<ContextKnowledgeBaseCreatePage />);

    expect(await screen.findByLabelText("Chunk length")).toHaveValue(254);
    expect(screen.getByLabelText("Chunk overlap")).toHaveValue(60);
    expect(screen.getByText(/supports up to 254 chunk tokens safely/i)).toBeVisible();

    await userEvent.clear(screen.getByLabelText("Chunk length"));
    await userEvent.type(screen.getByLabelText("Chunk length"), "300");

    expect(screen.getByText("Chunk length 300 exceeds the selected embeddings model safe maximum of 254 tokens.")).toBeVisible();

    await userEvent.type(screen.getByLabelText("Deployment slug"), "product-docs");
    await userEvent.type(screen.getByLabelText("Display name"), "Product Docs");
    await userEvent.type(screen.getByLabelText("Description"), "docs");
    await userEvent.selectOptions(await screen.findByLabelText("Schema profile"), "profile-rag");
    await userEvent.click(screen.getByRole("button", { name: "Create knowledge base" }));

    await waitFor(() => {
      expect(contextApi.createKnowledgeBase).not.toHaveBeenCalled();
    });
  });
});
