import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformDeploymentsPage from "./PlatformDeploymentsPage";
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
  createDeploymentProfile: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../api/context", () => ({
  listKnowledgeBases: vi.fn(),
}));

describe("PlatformDeploymentsPage", () => {
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

  it("renders deployment directory with view navigation", async () => {
    await renderWithAppProviders(<PlatformDeploymentsPage />);

    expect(await screen.findByRole("heading", { name: await t("platformControl.deployments.title"), level: 2 })).toBeVisible();
    const viewNav = screen.getByRole("navigation", { name: await t("platformControl.deployments.views.aria") });
    expect(screen.getByRole("button", { name: await t("platformControl.deployments.views.profiles") })).toHaveAttribute("aria-pressed", "true");
    expect(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.history") })).toBeVisible();
    expect(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.create") })).toBeVisible();
    expect(screen.queryByRole("table", { name: await t("platformControl.audit.tableAria") })).not.toBeInTheDocument();
    expect(screen.queryByText("Ready.")).not.toBeInTheDocument();
    expect(screen.getAllByText(await t("platformControl.badges.ready")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: await t("platformControl.actions.createDeployment") })).not.toBeInTheDocument();
  });

  it("filters deployments by search text", async () => {
    await renderWithAppProviders(<PlatformDeploymentsPage />);

    await userEvent.type(await screen.findByLabelText(await t("platformControl.filters.search")), "staging");

    expect(screen.getByRole("heading", { name: "Staging Profile" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Local Default" })).not.toBeInTheDocument();
  });

  it("switches between deployment page views", async () => {
    const user = userEvent.setup();
    await renderWithAppProviders(<PlatformDeploymentsPage />, { route: "/control/platform/deployments" });

    const viewNav = await screen.findByRole("navigation", { name: await t("platformControl.deployments.views.aria") });
    await user.click(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.history") }));

    expect(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.history") })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: await t("platformControl.sections.audit") })).toBeVisible();
    expect(await screen.findByText("2026-01-01T00:00:00+00:00")).toBeVisible();
    expect(screen.queryByLabelText(await t("platformControl.filters.search"))).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.create") }));

    expect(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.create") })).toHaveAttribute("aria-pressed", "true");
    const createHelp = await screen.findByText(await t("platformControl.deployments.createHelp"));
    expect(createHelp).toBeVisible();
    const createForm = createHelp.closest("form");
    expect(createForm).not.toBeNull();
    expect(within(createForm as HTMLElement).getByRole("button", { name: await t("platformControl.actions.createDeployment") })).toBeVisible();
    expect(screen.queryByText("2026-01-01T00:00:00+00:00")).not.toBeInTheDocument();
  });

  it("falls back to deployment profiles for invalid views", async () => {
    await renderWithAppProviders(<PlatformDeploymentsPage />, { route: "/control/platform/deployments?view=unknown" });

    const viewNav = await screen.findByRole("navigation", { name: await t("platformControl.deployments.views.aria") });
    expect(within(viewNav).getByRole("button", { name: await t("platformControl.deployments.views.profiles") })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByLabelText(await t("platformControl.filters.search"))).toBeVisible();
  });
});
