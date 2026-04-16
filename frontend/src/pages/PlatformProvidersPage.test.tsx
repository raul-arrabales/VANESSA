import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformProvidersPage from "./PlatformProvidersPage";
import * as platformApi from "../api/platform";
import { primePlatformControlMocks, providersFixture } from "../test/platformControlFixtures";

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
  createPlatformProvider: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../api/context", () => ({
  listKnowledgeBases: vi.fn(),
}));

describe("PlatformProvidersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    primePlatformControlMocks();
  });

  it("renders provider directory filters and keeps create/edit forms off the index", async () => {
    await renderWithAppProviders(<PlatformProvidersPage />);

    expect(await screen.findByRole("heading", { name: await t("platformControl.providers.title") })).toBeVisible();
    const viewNav = screen.getByRole("navigation", { name: await t("platformControl.providers.views.aria") });
    expect(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.providers") })).toHaveAttribute("aria-pressed", "true");
    expect(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.create") })).toBeVisible();
    expect(screen.queryByRole("link", { name: await t("platformControl.actions.createProvider") })).not.toBeInTheDocument();
    expect((await screen.findAllByText(await t("platformControl.providers.usedByDeployments"))).length).toBeGreaterThan(0);
    expect(document.querySelector(".platform-directory-grid")).toHaveClass("platform-provider-list");
    expect(screen.getAllByText(await t("platformControl.badges.local")).length).toBeGreaterThan(0);
    expect(screen.queryByLabelText(await t("platformControl.forms.provider.slug"))).not.toBeInTheDocument();
  });

  it("labels cloud providers distinctly from local providers", async () => {
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue([
      ...providersFixture,
      {
        ...providersFixture[0],
        id: "provider-cloud",
        slug: "openai-cloud-llm",
        provider_key: "openai_compatible_llm",
        provider_origin: "cloud",
        display_name: "OpenAI-compatible cloud LLM",
        endpoint_url: "https://api.example.com/v1",
      },
    ]);

    await renderWithAppProviders(<PlatformProvidersPage />);

    expect(await screen.findByRole("heading", { name: "OpenAI-compatible cloud LLM" })).toBeVisible();
    expect(screen.getByText(await t("platformControl.badges.cloud"))).toBeVisible();
  });

  it("filters the provider directory by search text", async () => {
    await renderWithAppProviders(<PlatformProvidersPage />);

    await userEvent.type(await screen.findByLabelText(await t("platformControl.filters.search")), "weaviate");

    expect(screen.getByRole("heading", { name: "Weaviate local" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "vLLM local gateway" })).not.toBeInTheDocument();
  });

  it("switches between provider page views", async () => {
    const user = userEvent.setup();
    await renderWithAppProviders(<PlatformProvidersPage />, { route: "/control/platform/providers" });

    const viewNav = await screen.findByRole("navigation", { name: await t("platformControl.providers.views.aria") });
    await user.click(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.create") }));

    expect(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.create") })).toHaveAttribute("aria-pressed", "true");
    const createHelp = await screen.findByText(await t("platformControl.providers.createHelp"));
    expect(createHelp).toBeVisible();
    const createForm = createHelp.closest("form");
    expect(createForm).not.toBeNull();
    expect(within(createForm as HTMLElement).getByRole("button", { name: await t("platformControl.actions.createProvider") })).toBeVisible();
    expect(screen.queryByText(await t("platformControl.providers.usedByDeployments"))).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.providers") }));

    expect(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.providers") })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByLabelText(await t("platformControl.filters.search"))).toBeVisible();
  });

  it("falls back to platform providers for invalid views", async () => {
    await renderWithAppProviders(<PlatformProvidersPage />, { route: "/control/platform/providers?view=unknown" });

    const viewNav = await screen.findByRole("navigation", { name: await t("platformControl.providers.views.aria") });
    expect(within(viewNav).getByRole("button", { name: await t("platformControl.providers.views.providers") })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByLabelText(await t("platformControl.filters.search"))).toBeVisible();
  });
});
