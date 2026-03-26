import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformControlPage from "./PlatformControlPage";
import * as platformApi from "../api/platform";
import { primePlatformControlMocks } from "../test/platformControlFixtures";

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

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../api/context", () => ({
  listKnowledgeBases: vi.fn(),
}));

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
    primePlatformControlMocks();
  });

  it("renders the overview dashboard and richer capability topology", async () => {
    await renderPage();

    expect(await screen.findByRole("heading", { name: await t("platformControl.title") })).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.capabilities"))).toBeVisible();
    expect((await screen.findAllByText(await t("platformControl.capabilities.servedArtifacts"))).length).toBeGreaterThan(0);
    expect(await screen.findByText("GPT-5 (+1)")).toBeVisible();
    const providerLinks = await screen.findAllByRole("link", { name: await t("platformControl.home.providersTitle") });
    expect(providerLinks.some((link) => link.getAttribute("href") === "/control/platform/providers")).toBe(true);
    const deploymentLinks = await screen.findAllByRole("link", { name: await t("platformControl.home.deploymentsTitle") });
    expect(deploymentLinks.some((link) => link.getAttribute("href") === "/control/platform/deployments")).toBe(true);
  });

  it("shows translated load errors", async () => {
    vi.mocked(platformApi.listPlatformCapabilities).mockRejectedValue(new Error("backend down"));

    await renderPage("es");

    expect(await screen.findByRole("heading", { name: "Control de plataforma" })).toBeVisible();
    expect(await screen.findByText("Error de solicitud: backend down")).toBeVisible();
  });
});
