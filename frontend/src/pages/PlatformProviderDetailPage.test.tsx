import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformProviderDetailPage from "./PlatformProviderDetailPage";
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
  updatePlatformProvider: vi.fn(),
  validatePlatformProvider: vi.fn(),
  deletePlatformProvider: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

describe("PlatformProviderDetailPage", () => {
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

  it("shows usage grouped by deployment and validates the provider", async () => {
    vi.mocked(platformApi.validatePlatformProvider).mockResolvedValue({
      provider: { id: "provider-1", slug: "vllm-local-gateway" },
      validation: {
        health: { reachable: true, status_code: 200 },
        resources_reachable: true,
        resources_status_code: 200,
      },
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-1" },
    );

    expect(await screen.findByText(await t("platformControl.sections.usage"))).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Local Default", level: 4 })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.validate") }));

    await waitFor(() => {
      expect(platformApi.validatePlatformProvider).toHaveBeenCalledWith("provider-1", "token");
    });
    expect(await screen.findByText(await t("platformControl.providers.resourcesReachable"))).toBeVisible();
  });

  it("saves provider changes from the detail page", async () => {
    vi.mocked(platformApi.updatePlatformProvider).mockResolvedValue(providersFixture[0]);

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-1" },
    );

    const nameField = await screen.findByLabelText(await t("platformControl.forms.provider.displayName"));
    await userEvent.clear(nameField);
    await userEvent.type(nameField, "Updated vLLM");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.saveProvider") }));

    await waitFor(() => {
      expect(platformApi.updatePlatformProvider).toHaveBeenCalledWith(
        "provider-1",
        expect.objectContaining({ display_name: "Updated vLLM" }),
        "token",
      );
    });
  });
});
