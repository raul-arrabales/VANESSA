import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformControlPage from "./PlatformControlPage";
import * as platformApi from "../api/platform";
import { deploymentsFixture, primePlatformControlMocks } from "../test/platformControlFixtures";

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
  await renderWithAppProviders(<PlatformControlPage />, { language, route: "/control/platform" });
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
    const sectionTabs = screen.getByRole("navigation", { name: await t("platformControl.navigation.aria") });
    expect(within(sectionTabs).getByRole("link", { name: await t("platformControl.navigation.home") })).toHaveAttribute("aria-current", "page");
    expect(within(sectionTabs).getByRole("link", { name: await t("platformControl.navigation.providers") })).toBeVisible();
    expect(within(sectionTabs).getByRole("link", { name: await t("platformControl.navigation.deployments") })).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.capabilities"))).toBeVisible();
    expect(document.querySelector(".platform-capability-grid")).toHaveClass("platform-capability-list");
    expect((await screen.findAllByText(await t("platformControl.capabilities.servedArtifacts"))).length).toBeGreaterThan(0);
    expect(await screen.findByText("GPT-5 (+1)")).toBeVisible();
    const providerLinks = await screen.findAllByRole("link", { name: await t("platformControl.home.providersTitle") });
    expect(providerLinks.some((link) => link.getAttribute("href") === "/control/platform/providers")).toBe(true);
    const deploymentLinks = await screen.findAllByRole("link", { name: await t("platformControl.home.deploymentsTitle") });
    expect(deploymentLinks.some((link) => link.getAttribute("href") === "/control/platform/deployments")).toBe(true);
  });

  it("activates another ready deployment from the overview quick switch", async () => {
    vi.mocked(platformApi.activateDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      is_active: true,
    });
    vi.mocked(platformApi.listPlatformDeployments)
      .mockResolvedValueOnce(deploymentsFixture)
      .mockResolvedValueOnce([
        { ...deploymentsFixture[0], is_active: false },
        { ...deploymentsFixture[1], is_active: true },
      ]);

    await renderPage();

    expect(await screen.findByText(await t("platformControl.quickSwitch.title"))).toBeVisible();
    expect(screen.getByLabelText(await t("platformControl.quickSwitch.deploymentLabel"))).toHaveValue("deployment-2");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.quickSwitch.activateSelected") }));

    const activationDialog = await screen.findByRole("dialog", {
      name: await t("platformControl.deployments.activationDialogTitle"),
    });
    expect(within(activationDialog).getByText("Local Default")).toBeVisible();
    expect(within(activationDialog).getByText("Staging Profile")).toBeVisible();

    await userEvent.click(within(activationDialog).getByRole("button", { name: await t("platformControl.actions.confirmActivate") }));

    await waitFor(() => {
      expect(platformApi.activateDeploymentProfile).toHaveBeenCalledWith("deployment-2", "token");
    });
    expect(await screen.findByText(await t("platformControl.feedback.activationSuccess", { name: "Staging Profile" }))).toBeVisible();
  });

  it("explains when there are no other ready deployments to switch to", async () => {
    vi.mocked(platformApi.listPlatformDeployments).mockResolvedValue([
      deploymentsFixture[0],
      {
        ...deploymentsFixture[1],
        configuration_status: {
          ...deploymentsFixture[1].configuration_status!,
          is_ready: false,
        },
      },
    ]);

    await renderPage();

    expect(await screen.findByText(await t("platformControl.quickSwitch.empty"))).toBeVisible();
    expect(screen.queryByRole("button", { name: await t("platformControl.quickSwitch.activateSelected") })).not.toBeInTheDocument();
  });

  it("shows translated load errors", async () => {
    vi.mocked(platformApi.listPlatformCapabilities).mockRejectedValue(new Error("backend down"));

    await renderPage("es");

    expect(await screen.findByRole("heading", { name: "Control de plataforma" })).toBeVisible();
    expect(await screen.findByText("Error de solicitud: backend down")).toBeVisible();
  });
});
