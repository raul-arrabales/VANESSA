import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformDeploymentCreatePage from "./PlatformDeploymentCreatePage";
import * as platformApi from "../api/platform";
import { deploymentsFixture, primePlatformControlMocks, providersFixture } from "../test/platformControlFixtures";

let mockUser: AuthUser | null = null;
const { navigateMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
}));

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
  listPlatformCapabilities: vi.fn(),
  listPlatformProviderFamilies: vi.fn(),
  listPlatformProviders: vi.fn(),
  listPlatformDeployments: vi.fn(),
  listPlatformActivationAudit: vi.fn(),
  createDeploymentProfile: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../api/context", () => ({
  listKnowledgeBases: vi.fn(),
}));

function buildDeploymentProviders() {
  return providersFixture.map((provider) =>
    provider.capability === "llm_inference" || provider.capability === "embeddings"
      ? {
          ...provider,
          provider_origin: "cloud" as const,
        }
      : provider,
  );
}

describe("PlatformDeploymentCreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigateMock.mockReset();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    primePlatformControlMocks();
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildDeploymentProviders());
  });

  it("creates multi-model deployment bindings with an explicit default", async () => {
    vi.mocked(platformApi.createDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      id: "deployment-3",
      slug: "cloud-profile",
      display_name: "Cloud Profile",
    });

    await renderWithAppProviders(<PlatformDeploymentCreatePage />);

    await userEvent.type(await screen.findByLabelText(await t("platformControl.forms.deployment.slug")), "cloud-profile");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.deployment.displayName")), "Cloud Profile");

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "LLM inference" })),
      "provider-1",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("GPT-5"));
    await userEvent.click(screen.getByLabelText("GPT-4.1"));
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "LLM inference" })),
      "gpt-4.1",
    );

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Embeddings" })),
      "provider-embeddings",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "Embeddings" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("text-embedding-3-small"));
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "Embeddings" })),
      "text-embedding-3-small",
    );

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Vector store" })),
      "provider-2",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "Vector store" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("Product Docs"));

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.createDeployment") }));

    await waitFor(() => {
      expect(platformApi.createDeploymentProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          slug: "cloud-profile",
          display_name: "Cloud Profile",
          bindings: expect.arrayContaining([
            expect.objectContaining({
              capability: "llm_inference",
              default_resource_id: "gpt-4.1",
              resources: expect.arrayContaining([
                expect.objectContaining({ id: "gpt-5", resource_kind: "model", ref_type: "managed_model" }),
                expect.objectContaining({ id: "gpt-4.1", resource_kind: "model", ref_type: "managed_model" }),
              ]),
            }),
            expect.objectContaining({
              capability: "embeddings",
              default_resource_id: "text-embedding-3-small",
              resources: expect.arrayContaining([
                expect.objectContaining({
                  id: "text-embedding-3-small",
                  resource_kind: "model",
                  ref_type: "managed_model",
                }),
              ]),
            }),
            expect.objectContaining({
              capability: "vector_store",
              resource_policy: expect.objectContaining({ selection_mode: "explicit" }),
              resources: expect.arrayContaining([
                expect.objectContaining({
                  id: "kb_primary",
                  resource_kind: "knowledge_base",
                  ref_type: "knowledge_base",
                  knowledge_base_id: "kb_primary",
                  provider_resource_id: "kb_product_docs",
                }),
              ]),
            }),
          ]),
        }),
        "token",
      );
    });

    expect(navigateMock).toHaveBeenCalledWith(
      "/control/platform/deployments/deployment-3",
      expect.objectContaining({
        state: expect.objectContaining({
          actionFeedback: expect.objectContaining({
            kind: "success",
            message: "Created deployment profile Cloud Profile.",
          }),
          deploymentSeed: expect.objectContaining({
            id: "deployment-3",
            slug: "cloud-profile",
            display_name: "Cloud Profile",
          }),
        }),
      }),
    );
  });

  it("allows adding an optional capability during deployment creation", async () => {
    vi.mocked(platformApi.listPlatformCapabilities).mockResolvedValue([
      {
        capability: "llm_inference",
        display_name: "LLM inference",
        description: "Normalized chat and generation capability.",
        required: true,
        active_provider: null,
      },
      {
        capability: "embeddings",
        display_name: "Embeddings",
        description: "Normalized text embeddings capability.",
        required: true,
        active_provider: null,
      },
      {
        capability: "vector_store",
        display_name: "Vector store",
        description: "Semantic retrieval capability.",
        required: true,
        active_provider: null,
      },
      {
        capability: "sandbox_execution",
        display_name: "Sandbox execution",
        description: "Sandbox capability.",
        required: false,
        active_provider: null,
      },
    ]);
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue([
      {
        id: "provider-1",
        slug: "vllm-local-gateway",
        provider_key: "vllm_local",
        provider_origin: "cloud",
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
      {
        id: "provider-embeddings",
        slug: "vllm-embeddings-local",
        provider_key: "vllm_embeddings_local",
        provider_origin: "cloud",
        capability: "embeddings",
        adapter_kind: "openai_compatible_embeddings",
        display_name: "vLLM embeddings local",
        description: "Primary embeddings endpoint.",
        endpoint_url: "http://llm:8000",
        healthcheck_url: "http://llm:8000/health",
        enabled: true,
        config: {},
        secret_refs: {},
      },
      {
        id: "provider-2",
        slug: "weaviate-local",
        provider_key: "weaviate_local",
        provider_origin: "local",
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
        id: "provider-sandbox",
        slug: "sandbox-local",
        provider_key: "sandbox_local",
        provider_origin: "local",
        capability: "sandbox_execution",
        adapter_kind: "sandbox_http",
        display_name: "Sandbox local",
        description: "Primary sandbox endpoint.",
        endpoint_url: "http://sandbox:8080",
        healthcheck_url: "http://sandbox:8080/health",
        enabled: true,
        config: {},
        secret_refs: {},
      },
    ]);
    vi.mocked(platformApi.createDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      id: "deployment-4",
      slug: "sandbox-profile",
      display_name: "Sandbox Profile",
    });

    await renderWithAppProviders(<PlatformDeploymentCreatePage />);

    await userEvent.click(await screen.findByRole("button", { name: await t("platformControl.actions.addCapability") }));
    const sandboxRow = await screen.findByTestId("deployment-binding-row-sandbox_execution");
    await userEvent.selectOptions(
      within(sandboxRow).getByLabelText(
        await t("platformControl.forms.deployment.providerForCapability", { capability: "Sandbox execution" }),
      ),
      "provider-sandbox",
    );

    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.deployment.slug")), "sandbox-profile");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.deployment.displayName")), "Sandbox Profile");
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "LLM inference" })),
      "provider-1",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("GPT-5"));
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "LLM inference" })),
      "gpt-5",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Embeddings" })),
      "provider-embeddings",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "Embeddings" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("text-embedding-3-small"));
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "Embeddings" })),
      "text-embedding-3-small",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Vector store" })),
      "provider-2",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "Vector store" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("Product Docs"));

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.createDeployment") }));

    await waitFor(() => {
      expect(platformApi.createDeploymentProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          bindings: expect.arrayContaining([
            expect.objectContaining({
              capability: "sandbox_execution",
              provider_id: "provider-sandbox",
            }),
          ]),
        }),
        "token",
      );
    });
  });
});
