import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformProviderCreatePage from "./PlatformProviderCreatePage";
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

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

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

describe("PlatformProviderCreatePage", () => {
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

  it("creates a provider instance from the dedicated create page", async () => {
    vi.mocked(platformApi.createPlatformProvider).mockResolvedValue(providersFixture[0]);

    await renderWithAppProviders(<PlatformProviderCreatePage />);
    const providerFamilyLabel = await t("platformControl.forms.provider.family");

    await userEvent.selectOptions(await screen.findByLabelText(providerFamilyLabel), "vllm_local");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.slug")), "custom-vllm");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.displayName")), "Custom vLLM");
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
});
