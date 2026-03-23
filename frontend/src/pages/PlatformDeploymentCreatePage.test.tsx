import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformDeploymentCreatePage from "./PlatformDeploymentCreatePage";
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
  createDeploymentProfile: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

describe("PlatformDeploymentCreatePage", () => {
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

  it("creates multi-model deployment bindings with an explicit default", async () => {
    vi.mocked(platformApi.createDeploymentProfile).mockResolvedValue({
      ...deploymentsFixture[1],
      id: "deployment-3",
      slug: "cloud-profile",
      display_name: "Cloud Profile",
    });

    await renderWithAppProviders(<PlatformDeploymentCreatePage />);

    await userEvent.type(await screen.findByLabelText(await t("platformControl.forms.deployment.slug")), "cloud-profile");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.deployment.displayName")), "Cloud Profile");

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "LLM inference" })),
      "provider-1",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.servedModelsForCapability", { capability: "LLM inference" })),
      ["gpt-5", "gpt-4.1"],
    );
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultServedModelForCapability", { capability: "LLM inference" })),
      "gpt-4.1",
    );

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Embeddings" })),
      "provider-embeddings",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.servedModelsForCapability", { capability: "Embeddings" })),
      ["text-embedding-3-small"],
    );
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultServedModelForCapability", { capability: "Embeddings" })),
      "text-embedding-3-small",
    );

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Vector store" })),
      "provider-2",
    );

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.createDeployment") }));

    await waitFor(() => {
      expect(platformApi.createDeploymentProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          slug: "cloud-profile",
          display_name: "Cloud Profile",
          bindings: expect.arrayContaining([
            expect.objectContaining({
              capability: "llm_inference",
              served_model_ids: ["gpt-5", "gpt-4.1"],
              default_served_model_id: "gpt-4.1",
            }),
            expect.objectContaining({
              capability: "embeddings",
              served_model_ids: ["text-embedding-3-small"],
              default_served_model_id: "text-embedding-3-small",
            }),
          ]),
        }),
        "token",
      );
    });
  });
});
