import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformControlPage from "./PlatformControlPage";
import * as platformApi from "../api/platform";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("../api/platform", () => ({
  listPlatformCapabilities: vi.fn(),
  listPlatformProviderFamilies: vi.fn(),
  listPlatformProviders: vi.fn(),
  listPlatformDeployments: vi.fn(),
  listPlatformActivationAudit: vi.fn(),
  validatePlatformProvider: vi.fn(),
  createPlatformProvider: vi.fn(),
  updatePlatformProvider: vi.fn(),
  deletePlatformProvider: vi.fn(),
  createDeploymentProfile: vi.fn(),
  updateDeploymentProfile: vi.fn(),
  cloneDeploymentProfile: vi.fn(),
  deleteDeploymentProfile: vi.fn(),
  activateDeploymentProfile: vi.fn(),
}));

const capabilitiesFixture = [
  {
    capability: "llm_inference",
    display_name: "LLM inference",
    description: "Normalized chat and generation capability.",
    required: true,
    active_provider: {
      id: "provider-1",
      slug: "vllm-local-gateway",
      provider_key: "vllm_local",
      display_name: "vLLM local gateway",
      deployment_profile_id: "deployment-1",
      deployment_profile_slug: "local-default",
    },
  },
  {
    capability: "embeddings",
    display_name: "Embeddings",
    description: "Normalized text embeddings capability.",
    required: true,
    active_provider: {
      id: "provider-embeddings",
      slug: "vllm-embeddings-local",
      provider_key: "vllm_embeddings_local",
      display_name: "vLLM embeddings local",
      deployment_profile_id: "deployment-1",
      deployment_profile_slug: "local-default",
    },
  },
  {
    capability: "vector_store",
    display_name: "Vector store",
    description: "Semantic retrieval capability.",
    required: true,
    active_provider: {
      id: "provider-2",
      slug: "weaviate-local",
      provider_key: "weaviate_local",
      display_name: "Weaviate local",
      deployment_profile_id: "deployment-1",
      deployment_profile_slug: "local-default",
    },
  },
];

const providerFamiliesFixture = [
  {
    provider_key: "vllm_local",
    capability: "llm_inference",
    adapter_kind: "openai_compatible_llm",
    display_name: "vLLM local gateway",
    description: "Local vLLM family.",
  },
  {
    provider_key: "vllm_embeddings_local",
    capability: "embeddings",
    adapter_kind: "openai_compatible_embeddings",
    display_name: "vLLM embeddings local",
    description: "Local embeddings family.",
  },
  {
    provider_key: "weaviate_local",
    capability: "vector_store",
    adapter_kind: "weaviate_http",
    display_name: "Weaviate local",
    description: "Local Weaviate family.",
  },
];

const providersFixture = [
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
  {
    id: "provider-embeddings",
    slug: "vllm-embeddings-local",
    provider_key: "vllm_embeddings_local",
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
];

const deploymentsFixture = [
  {
    id: "deployment-1",
    slug: "local-default",
    display_name: "Local Default",
    description: "Default local profile.",
    is_active: true,
    bindings: [
      {
        capability: "llm_inference",
        provider: {
          id: "provider-1",
          slug: "vllm-local-gateway",
          provider_key: "vllm_local",
          display_name: "vLLM local gateway",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_llm",
        },
        config: {},
      },
      {
        capability: "embeddings",
        provider: {
          id: "provider-embeddings",
          slug: "vllm-embeddings-local",
          provider_key: "vllm_embeddings_local",
          display_name: "vLLM embeddings local",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_embeddings",
        },
        config: {},
      },
      {
        capability: "vector_store",
        provider: {
          id: "provider-2",
          slug: "weaviate-local",
          provider_key: "weaviate_local",
          display_name: "Weaviate local",
          endpoint_url: "http://weaviate:8080",
          enabled: true,
          adapter_kind: "weaviate_http",
        },
        config: {},
      },
    ],
  },
  {
    id: "deployment-2",
    slug: "staging-profile",
    display_name: "Staging Profile",
    description: "Alternate profile.",
    is_active: false,
    bindings: [
      {
        capability: "llm_inference",
        provider: {
          id: "provider-1",
          slug: "vllm-local-gateway",
          provider_key: "vllm_local",
          display_name: "vLLM local gateway",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_llm",
        },
        config: {},
      },
      {
        capability: "embeddings",
        provider: {
          id: "provider-embeddings",
          slug: "vllm-embeddings-local",
          provider_key: "vllm_embeddings_local",
          display_name: "vLLM embeddings local",
          endpoint_url: "http://llm:8000",
          enabled: true,
          adapter_kind: "openai_compatible_embeddings",
        },
        config: {},
      },
      {
        capability: "vector_store",
        provider: {
          id: "provider-2",
          slug: "weaviate-local",
          provider_key: "weaviate_local",
          display_name: "Weaviate local",
          endpoint_url: "http://weaviate:8080",
          enabled: true,
          adapter_kind: "weaviate_http",
        },
        config: {},
      },
    ],
  },
];

const activationAuditFixture = [
  {
    id: "audit-1",
    deployment_profile: {
      id: "deployment-1",
      slug: "local-default",
      display_name: "Local Default",
    },
    previous_deployment_profile: null,
    activated_by_user_id: 1,
    activated_at: "2026-01-01T00:00:00+00:00",
  },
];

async function renderPage(language: "en" | "es" = "en"): Promise<void> {
  await renderWithAppProviders(<PlatformControlPage />, { language });
}

describe("PlatformControlPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    vi.mocked(platformApi.listPlatformCapabilities).mockResolvedValue(capabilitiesFixture);
    vi.mocked(platformApi.listPlatformProviderFamilies).mockResolvedValue(providerFamiliesFixture);
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(providersFixture);
    vi.mocked(platformApi.listPlatformDeployments).mockResolvedValue(deploymentsFixture);
    vi.mocked(platformApi.listPlatformActivationAudit).mockResolvedValue(activationAuditFixture);
  });

  it("loads and renders capability, provider, deployment, and audit data", async () => {
    await renderPage();

    expect(await screen.findByRole("heading", { name: await t("platformControl.title") })).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.capabilities"))).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.providers"))).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.deployments"))).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.audit"))).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Embeddings" })).toBeVisible();
    expect((await screen.findAllByText("2026-01-01T00:00:00+00:00")).length).toBeGreaterThan(0);
    expect(await screen.findByRole("heading", { name: "Local Default" })).toBeVisible();
    expect((await screen.findAllByText("vLLM local gateway")).length).toBeGreaterThan(0);
  });

  it("creates a provider instance from the admin form", async () => {
    vi.mocked(platformApi.createPlatformProvider).mockResolvedValue(providersFixture[0]);

    await renderPage();
    const providerFamilyLabel = await t("platformControl.forms.provider.family");
    await waitFor(() => {
      expect(screen.getByLabelText(providerFamilyLabel).querySelectorAll("option").length).toBeGreaterThan(1);
    });

    await userEvent.selectOptions(
      screen.getByLabelText(providerFamilyLabel),
      "vllm_local",
    );
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.slug")), "custom-vllm");
    await userEvent.type(screen.getAllByLabelText(await t("platformControl.forms.provider.displayName"))[0], "Custom vLLM");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.endpoint")), "http://llm-alt:8000");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.createProvider") }));

    await waitFor(() => {
      expect(platformApi.createPlatformProvider).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_key: "vllm_local",
          slug: "custom-vllm",
          display_name: "Custom vLLM",
        }),
        "token",
      );
    });
  });

  it("validates providers and shows the returned status", async () => {
    vi.mocked(platformApi.validatePlatformProvider).mockResolvedValue({
      provider: { id: "provider-1", slug: "vllm-local-gateway" },
      validation: {
        health: { reachable: true, status_code: 200 },
        models_reachable: true,
        models_status_code: 200,
      },
    });

    await renderPage();
    const validateButtons = await screen.findAllByRole("button", { name: await t("platformControl.actions.validate") });
    await userEvent.click(validateButtons[0]);

    await waitFor(() => {
      expect(platformApi.validatePlatformProvider).toHaveBeenCalledWith("provider-1", "token");
    });
    expect(await screen.findByText(await t("platformControl.providers.modelsReachable"))).toBeVisible();
  });

  it("clones a deployment profile from the admin form", async () => {
    vi.mocked(platformApi.cloneDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      id: "deployment-3",
      slug: "staging-profile-copy",
      display_name: "Staging Profile Copy",
    });

    await renderPage();
    const cloneButtons = await screen.findAllByRole("button", { name: await t("platformControl.actions.clone") });
    await userEvent.click(cloneButtons[0]);

    const slugField = screen.getAllByLabelText(await t("platformControl.forms.deployment.slug"))[0];
    expect(slugField).toHaveValue("local-default-copy");
    await userEvent.clear(slugField);
    await userEvent.type(slugField, "staging-profile-copy");
    const nameField = screen.getAllByLabelText(await t("platformControl.forms.deployment.displayName"))[1];
    await userEvent.clear(nameField);
    await userEvent.type(nameField, "Staging Profile Copy");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.cloneDeployment") }));

    await waitFor(() => {
      expect(platformApi.cloneDeploymentProfile).toHaveBeenCalledWith(
        "deployment-1",
        expect.objectContaining({
          slug: "staging-profile-copy",
          display_name: "Staging Profile Copy",
        }),
        "token",
      );
    });
  });

  it("renders deployment bindings from the capability registry", async () => {
    await renderPage();

    expect(
      await screen.findByLabelText(
        await t("platformControl.forms.deployment.providerForCapability", { capability: "Embeddings" }),
      ),
    ).toBeVisible();
  });

  it("confirms activation, activates the deployment, and refreshes state", async () => {
    vi.mocked(platformApi.activateDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      is_active: true,
    });
    vi.mocked(platformApi.listPlatformCapabilities)
      .mockResolvedValueOnce(capabilitiesFixture)
      .mockResolvedValueOnce(capabilitiesFixture);
    vi.mocked(platformApi.listPlatformProviderFamilies)
      .mockResolvedValueOnce(providerFamiliesFixture)
      .mockResolvedValueOnce(providerFamiliesFixture);
    vi.mocked(platformApi.listPlatformProviders)
      .mockResolvedValueOnce(providersFixture)
      .mockResolvedValueOnce(providersFixture);
    vi.mocked(platformApi.listPlatformDeployments)
      .mockResolvedValueOnce(deploymentsFixture)
      .mockResolvedValueOnce([
        { ...deploymentsFixture[0], is_active: false },
        { ...deploymentsFixture[1], is_active: true },
      ]);
    vi.mocked(platformApi.listPlatformActivationAudit)
      .mockResolvedValueOnce(activationAuditFixture)
      .mockResolvedValueOnce([
        {
          ...activationAuditFixture[0],
          id: "audit-2",
          deployment_profile: {
            id: "deployment-2",
            slug: "staging-profile",
            display_name: "Staging Profile",
          },
        },
      ]);

    await renderPage();
    await userEvent.click(await screen.findByRole("button", { name: await t("platformControl.actions.activate") }));
    expect(await screen.findByText(await t("platformControl.deployments.confirmActivation"))).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.confirmActivate") }));

    await waitFor(() => {
      expect(platformApi.activateDeploymentProfile).toHaveBeenCalledWith("deployment-2", "token");
    });
    expect(await screen.findByText(await t("platformControl.feedback.activationSuccess", { name: "Staging Profile" }))).toBeVisible();
  });

  it("shows load errors and resolves Spanish translations", async () => {
    vi.mocked(platformApi.listPlatformCapabilities).mockRejectedValue(new Error("backend down"));

    await renderPage("es");

    expect(await screen.findByRole("heading", { name: "Control de plataforma" })).toBeVisible();
    expect(await screen.findByText("Error de solicitud: backend down")).toBeVisible();
  });
});
