import { screen } from "@testing-library/react";
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

  it("renders deployment directory and activation audit", async () => {
    await renderWithAppProviders(<PlatformDeploymentsPage />);

    expect(await screen.findByRole("heading", { name: await t("platformControl.deployments.title"), level: 2 })).toBeVisible();
    expect(await screen.findByText(await t("platformControl.sections.audit"))).toBeVisible();
    expect(await screen.findByText("2026-01-01T00:00:00+00:00")).toBeVisible();
    expect(await screen.findByRole("link", { name: await t("platformControl.actions.createDeployment") })).toHaveAttribute(
      "href",
      "/control/platform/deployments/new",
    );
  });

  it("filters deployments by search text", async () => {
    await renderWithAppProviders(<PlatformDeploymentsPage />);

    await userEvent.type(await screen.findByLabelText(await t("platformControl.filters.search")), "staging");

    expect(screen.getByRole("heading", { name: "Staging Profile" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Local Default" })).not.toBeInTheDocument();
  });
});
