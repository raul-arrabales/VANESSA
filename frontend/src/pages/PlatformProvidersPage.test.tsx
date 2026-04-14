import { screen } from "@testing-library/react";
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
    expect(await screen.findByRole("link", { name: await t("platformControl.actions.createProvider") })).toHaveAttribute(
      "href",
      "/control/platform/providers/new",
    );
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
        provider_key: "openai_compatible_cloud_llm",
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
});
