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
const { navigateMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
}));

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
    useNavigate: () => navigateMock,
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
    navigateMock.mockReset();
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
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("GPT-5"));
    await userEvent.click(screen.getByLabelText("GPT-4.1"));
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "LLM inference" })),
      "gpt-4.1",
    );

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Embeddings" })),
      "provider-embeddings",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "Embeddings" }),
      }),
    );
    await userEvent.click(screen.getByLabelText("text-embedding-3-small"));
    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "Embeddings" })),
      "text-embedding-3-small",
    );

    await userEvent.selectOptions(
      screen.getByLabelText(await t("platformControl.forms.deployment.providerForCapability", { capability: "Vector store" })),
      "provider-2",
    );
    await userEvent.type(
      screen.getByLabelText(await t("platformControl.forms.deployment.explicitResources")),
      "kb_primary",
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
              default_resource_id: "gpt-4.1",
              resources: expect.arrayContaining([
                expect.objectContaining({ id: "gpt-5", resource_kind: "model", ref_type: "managed_model" }),
                expect.objectContaining({ id: "gpt-4.1", resource_kind: "model", ref_type: "managed_model" }),
              ]),
            }),
            expect.objectContaining({
              capability: "embeddings",
              default_resource_id: "text-embedding-3-small",
              resources: expect.arrayContaining([
                expect.objectContaining({
                  id: "text-embedding-3-small",
                  resource_kind: "model",
                  ref_type: "managed_model",
                }),
              ]),
            }),
            expect.objectContaining({
              capability: "vector_store",
              resource_policy: expect.objectContaining({ selection_mode: "explicit" }),
              resources: expect.arrayContaining([
                expect.objectContaining({
                  id: "kb_primary",
                  resource_kind: "index",
                  ref_type: "provider_resource",
                }),
              ]),
            }),
          ]),
        }),
        "token",
      );
    });

    expect(navigateMock).toHaveBeenCalledWith(
      "/control/platform/deployments/deployment-3",
      expect.objectContaining({
        state: expect.objectContaining({
          actionFeedback: expect.objectContaining({
            kind: "success",
            message: "Created deployment profile Cloud Profile.",
          }),
          deploymentSeed: expect.objectContaining({
            id: "deployment-3",
            slug: "cloud-profile",
            display_name: "Cloud Profile",
          }),
        }),
      }),
    );
  });
});
