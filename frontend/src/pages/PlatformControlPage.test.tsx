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
  listPlatformProviders: vi.fn(),
  listPlatformDeployments: vi.fn(),
  validatePlatformProvider: vi.fn(),
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
    ],
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
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(providersFixture);
    vi.mocked(platformApi.listPlatformDeployments).mockResolvedValue(deploymentsFixture);
  });

  it("loads and renders capability, provider, and deployment data", async () => {
    await renderPage();

    expect(await screen.findByRole("heading", { name: await t("platformControl.title") })).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.capabilities"))).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.providers"))).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.deployments"))).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Local Default" })).toBeVisible();
    expect(await screen.findByRole("heading", { name: "LLM inference" })).toBeVisible();
    expect((await screen.findAllByText("vLLM local gateway")).length).toBeGreaterThan(0);
    expect(await screen.findByRole("button", { name: await t("platformControl.actions.activate") })).toBeVisible();
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
    await userEvent.click(await screen.findByRole("button", { name: await t("platformControl.actions.validate") }));

    await waitFor(() => {
      expect(platformApi.validatePlatformProvider).toHaveBeenCalledWith("provider-1", "token");
    });
    expect(await screen.findByText(await t("platformControl.providers.modelsReachable"))).toBeVisible();
  });

  it("confirms activation, activates the deployment, and refreshes state", async () => {
    vi.mocked(platformApi.activateDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      is_active: true,
    });
    vi.mocked(platformApi.listPlatformCapabilities)
      .mockResolvedValueOnce(capabilitiesFixture)
      .mockResolvedValueOnce(capabilitiesFixture);
    vi.mocked(platformApi.listPlatformProviders)
      .mockResolvedValueOnce(providersFixture)
      .mockResolvedValueOnce(providersFixture);
    vi.mocked(platformApi.listPlatformDeployments)
      .mockResolvedValueOnce(deploymentsFixture)
      .mockResolvedValueOnce([
        { ...deploymentsFixture[0], is_active: false },
        { ...deploymentsFixture[1], is_active: true },
      ]);

    await renderPage();
    await userEvent.click(await screen.findByRole("button", { name: await t("platformControl.actions.activate") }));
    expect(await screen.findByText(await t("platformControl.deployments.confirmActivation"))).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.confirmActivate") }));

    await waitFor(() => {
      expect(platformApi.activateDeploymentProfile).toHaveBeenCalledWith("deployment-2", "token");
    });
    expect(await screen.findByText(await t("platformControl.feedback.activationSuccess", { name: "Staging Profile" }))).toBeVisible();
    expect(await screen.findAllByText(await t("platformControl.badges.active"))).toHaveLength(2);
  });

  it("shows load errors and resolves Spanish translations", async () => {
    vi.mocked(platformApi.listPlatformCapabilities).mockRejectedValue(new Error("backend down"));

    await renderPage("es");

    expect(await screen.findByRole("heading", { name: "Control de plataforma" })).toBeVisible();
    expect(await screen.findByText("Error de solicitud: backend down")).toBeVisible();
  });
});
