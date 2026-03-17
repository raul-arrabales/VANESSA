import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AuthUser } from "./auth/types";
import App from "./App";
import { renderWithAppProviders } from "./test/renderWithAppProviders";
import { t } from "./test/translation";

let mockUser: AuthUser | null = null;

vi.mock("./auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
    activatePendingUser: vi.fn(),
    listPendingUsers: vi.fn(),
    updateUserRole: vi.fn(),
  }),
}));


vi.mock("./runtime/RuntimeModeProvider", () => ({
  useRuntimeMode: () => ({
    mode: "offline",
    isLoading: false,
    isSaving: false,
    error: "",
    setMode: vi.fn(),
  }),
}));
vi.mock("./api/models", () => ({
  listModelCatalog: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  listModelAssignments: vi.fn(async () => [{ scope: "superadmin", model_ids: ["gpt-4"] }]),
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
  listEnabledModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  runInference: vi.fn(),
  listModelCredentials: vi.fn(async () => []),
  createModelCredential: vi.fn(),
  revokeModelCredential: vi.fn(),
  registerManagedModel: vi.fn(),
  listAvailableManagedModels: vi.fn(async () => []),
}));
vi.mock("./api/platform", () => ({
  listPlatformCapabilities: vi.fn(async () => [
    {
      capability: "llm_inference",
      display_name: "LLM inference",
      description: "desc",
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
  ]),
  listPlatformProviders: vi.fn(async () => [
    {
      id: "provider-1",
      slug: "vllm-local-gateway",
      provider_key: "vllm_local",
      capability: "llm_inference",
      adapter_kind: "openai_compatible_llm",
      display_name: "vLLM local gateway",
      description: "desc",
      endpoint_url: "http://llm:8000",
      healthcheck_url: "http://llm:8000/health",
      enabled: true,
      config: {},
    },
  ]),
  listPlatformDeployments: vi.fn(async () => [
    {
      id: "deployment-1",
      slug: "local-default",
      display_name: "Local Default",
      description: "desc",
      is_active: true,
      bindings: [],
    },
  ]),
  validatePlatformProvider: vi.fn(),
  activateDeploymentProfile: vi.fn(),
}));
vi.mock("./api/quoteAdmin", () => ({
  fetchQuoteSummary: vi.fn(async () => ({
    total: 2,
    active: 2,
    approved: 2,
    by_language: [],
    by_tone: [],
    by_origin: [],
  })),
  fetchQuotes: vi.fn(async () => ({
    items: [],
    page: 1,
    page_size: 10,
    total: 0,
    filters: {},
  })),
  fetchQuoteById: vi.fn(),
  createQuote: vi.fn(),
  updateQuote: vi.fn(),
}));

describe("App superadmin models route", () => {
  it("renders the page for superadmin", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    expect(await screen.findByRole("heading", { name: await t("models.title") })).toBeVisible();
  });

  it("blocks non-superadmin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/system-health" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("renders the platform control page for superadmin", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/platform" });

    expect(await screen.findByRole("heading", { name: await t("platformControl.title") })).toBeVisible();
  });

  it("blocks admin users from the platform control route", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/platform" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("renders the quote management page for admin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/quotes" });

    expect(await screen.findByRole("heading", { name: await t("quoteAdmin.title") })).toBeVisible();
  });

  it("blocks regular users from the quote management route", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/quotes" });

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("falls through removed legacy routes to not-found", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/chat" });

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeVisible();
  });

  it("always shows Home as the first breadcrumb link", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    const breadcrumbLinks = await screen.findAllByRole("link", { name: await t("nav.home") });
    expect(breadcrumbLinks[0]).toHaveAttribute("href", "/");
  });

  it("renders the control breadcrumb with the control panel label", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderWithAppProviders(<App />, { route: "/control/models" });

    expect(await screen.findByRole("link", { name: await t("nav.controlPanel") })).toHaveAttribute("href", "/control");
  });
});
