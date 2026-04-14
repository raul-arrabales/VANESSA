import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformDeploymentDetailPage from "./PlatformDeploymentDetailPage";
import * as platformApi from "../api/platform";
import * as modelopsApi from "../api/modelops";
import {
  activationAuditFixture,
  deploymentsFixture,
  llmModelsFixture,
  primePlatformControlMocks,
  providersFixture,
} from "../test/platformControlFixtures";

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
  patchDeploymentProfileIdentity: vi.fn(),
  upsertDeploymentBinding: vi.fn(),
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

describe("PlatformDeploymentDetailPage", () => {
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

  it("shows deployment topology and activates an inactive deployment", async () => {
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
    vi.mocked(platformApi.listPlatformActivationAudit)
      .mockResolvedValueOnce(activationAuditFixture)
      .mockResolvedValueOnce([
        {
          ...activationAuditFixture[0],
          id: "audit-2",
          deployment_profile: {
            id: "deployment-2",
            slug: "staging-profile",
            display_name: "Staging Profile",
          },
        },
      ]);

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-2" },
    );

    const topologyTable = await screen.findByRole("table", {
      name: await t("platformControl.deployments.tableAria", { name: "Staging Profile" }),
    });
    expect(within(topologyTable).getByText("GPT-5")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.activate") }));

    const activationDialog = await screen.findByRole("dialog", {
      name: await t("platformControl.deployments.activationDialogTitle"),
    });
    expect(within(activationDialog).getByText("Local Default")).toBeVisible();
    expect(within(activationDialog).getByText("Staging Profile")).toBeVisible();
    expect(platformApi.activateDeploymentProfile).not.toHaveBeenCalled();

    await userEvent.click(within(activationDialog).getByRole("button", { name: await t("platformControl.actions.confirmActivate") }));

    await waitFor(() => {
      expect(platformApi.activateDeploymentProfile).toHaveBeenCalledWith("deployment-2", "token");
    });
    expect(await screen.findByText(await t("platformControl.feedback.activationSuccess", { name: "Staging Profile" }))).toBeVisible();
  });

  it("clones a deployment profile from the detail page", async () => {
    const clonedDeployment = {
      ...deploymentsFixture[1],
      id: "deployment-3",
      slug: "staging-profile-copy",
      display_name: "Staging Profile Copy",
    };
    vi.mocked(platformApi.cloneDeploymentProfile).mockResolvedValue(clonedDeployment);

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-1" },
    );

    const slugField = await screen.findAllByLabelText(await t("platformControl.forms.deployment.slug"));
    await userEvent.clear(slugField[1]);
    await userEvent.type(slugField[1], "staging-profile-copy");
    const nameField = await screen.findAllByLabelText(await t("platformControl.forms.deployment.displayName"));
    await userEvent.clear(nameField[1]);
    await userEvent.type(nameField[1], "Staging Profile Copy");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.cloneDeployment") }));

    await waitFor(() => {
      expect(platformApi.cloneDeploymentProfile).toHaveBeenCalledWith(
        "deployment-1",
        expect.objectContaining({
          slug: "staging-profile-copy",
          display_name: "Staging Profile Copy",
        }),
        "token",
      );
    });

    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("Cloned deployment profile Staging Profile Copy.")).toBeVisible();
    expect(screen.queryByText(await t("platformControl.deployments.notFound"))).toBeNull();
    expect(await screen.findByRole("table", {
      name: await t("platformControl.deployments.tableAria", { name: "Staging Profile Copy" }),
    })).toBeVisible();
    await waitFor(() => {
      expect(platformApi.listPlatformDeployments).toHaveBeenCalledTimes(2);
    });
  });

  it("renders one binding row per capability and saves a single binding section independently", async () => {
    vi.mocked(platformApi.upsertDeploymentBinding).mockResolvedValue(deploymentsFixture[0]);

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-1" },
    );

    const llmRow = await screen.findByTestId("deployment-binding-row-llm_inference");
    const embeddingsRow = screen.getByTestId("deployment-binding-row-embeddings");
    const vectorRow = screen.getByTestId("deployment-binding-row-vector_store");
    const identityRow = screen.getByTestId("deployment-identity-row");

    expect(identityRow).toHaveClass("panel-nested");
    expect(llmRow).toHaveClass("panel-nested");
    expect(embeddingsRow).toHaveClass("panel-nested");
    expect(vectorRow).toHaveClass("panel-nested");

    expect(
      within(llmRow).getByLabelText(
        await t("platformControl.forms.deployment.providerForCapability", { capability: "LLM inference" }),
      ),
    ).toBeVisible();
    expect(
      within(llmRow).getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "LLM inference" }),
      }),
    ).toBeVisible();
    expect(
      within(llmRow).getByLabelText(
        await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "LLM inference" }),
      ),
    ).toBeVisible();
    expect(
      within(embeddingsRow).getByRole("button", {
        name: await t("platformControl.forms.deployment.resourcesForCapability", { capability: "Embeddings" }),
      }),
    ).toBeVisible();
    expect(
      within(vectorRow).getByLabelText(await t("platformControl.forms.deployment.vectorSelectionMode")),
    ).toBeVisible();

    await userEvent.click(within(llmRow).getByRole("button", { name: await t("platformControl.actions.saveBinding") }));

    await waitFor(() => {
      expect(platformApi.upsertDeploymentBinding).toHaveBeenCalledWith(
        "deployment-1",
        "llm_inference",
        expect.objectContaining({
          provider_id: "provider-1",
          default_resource_id: "gpt-5",
          resources: expect.arrayContaining([
            expect.objectContaining({ id: "gpt-5", managed_model_id: "gpt-5" }),
            expect.objectContaining({ id: "gpt-4.1", managed_model_id: "gpt-4.1" }),
          ]),
        }),
        "token",
      );
    });
  });

  it("saves deployment identity independently from capability bindings", async () => {
    vi.mocked(platformApi.patchDeploymentProfileIdentity).mockResolvedValue({
      ...deploymentsFixture[0],
      display_name: "Local Default Updated",
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-1" },
    );

    const nameField = (await screen.findAllByLabelText(await t("platformControl.forms.deployment.displayName")))[0];
    await userEvent.clear(nameField);
    await userEvent.type(nameField, "Local Default Updated");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.saveDeploymentIdentity") }));

    await waitFor(() => {
      expect(platformApi.patchDeploymentProfileIdentity).toHaveBeenCalledWith(
        "deployment-1",
        expect.objectContaining({
          slug: "local-default",
          display_name: "Local Default Updated",
        }),
        "token",
      );
    });
  });

  it("explains when a selected provider has a loaded model that is not yet eligible for binding", async () => {
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(
      providersFixture.map((provider) =>
        provider.id === "provider-embeddings"
          ? {
              ...provider,
              loaded_managed_model_id: "sentence-transformers--all-MiniLM-L6-v2",
              loaded_managed_model_name: "all-MiniLM-L6-v2",
            }
          : provider,
      ),
    );
    vi.mocked(modelopsApi.listModelOpsModels).mockImplementation(async (_token, options) => {
      if (options?.capability === "llm_inference") {
        return llmModelsFixture;
      }
      if (options?.capability === "embeddings") {
        return [];
      }
      return llmModelsFixture;
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-1" },
    );

    expect(await screen.findByText(/vLLM embeddings local currently has all-MiniLM-L6-v2 loaded/i)).toBeVisible();
    expect(screen.getAllByText("GPT-5").length).toBeGreaterThan(0);

    const embeddingsDefaultSelect = screen.getByLabelText(
      await t("platformControl.forms.deployment.defaultResourceForCapability", { capability: "Embeddings" }),
    );
    expect(embeddingsDefaultSelect).toBeDisabled();
  });

  it("explains when no eligible model resources are available for the selected capability", async () => {
    vi.mocked(modelopsApi.listModelOpsModels).mockImplementation(async (_token, options) => {
      if (options?.capability === "llm_inference") {
        return llmModelsFixture;
      }
      if (options?.capability === "embeddings") {
        return [];
      }
      return llmModelsFixture;
    });

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-1" },
    );

    expect(await screen.findByText(/No ModelOps-eligible Embeddings resources are currently available for binding\./i)).toBeVisible();
  });

  it("shows not found for a direct unknown deployment route without a seeded deployment", async () => {
    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/deployments/:deploymentId" element={<PlatformDeploymentDetailPage />} />
      </Routes>,
      { route: "/control/platform/deployments/deployment-missing" },
    );

    expect((await screen.findAllByText(await t("platformControl.deployments.notFound"))).length).toBeGreaterThan(0);
  });
});
