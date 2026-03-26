import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformProviderDetailPage from "./PlatformProviderDetailPage";
import * as platformApi from "../api/platform";
import * as modelOpsModelsApi from "../api/modelops/models";
import { embeddingsModelsFixture, primePlatformControlMocks, providersFixture } from "../test/platformControlFixtures";

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
  assignPlatformProviderLoadedModel: vi.fn(),
  clearPlatformProviderLoadedModel: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../api/modelops/models", () => ({
  listModelOpsModels: vi.fn(),
}));

const localEmbeddingsModel = {
  ...embeddingsModelsFixture[0],
  id: "sentence-transformers--all-MiniLM-L6-v2",
  name: "sentence-transformers/all-MiniLM-L6-v2",
  backend: "local" as const,
  source: "huggingface",
  availability: "offline_ready" as const,
};

function buildEmbeddingsProvider(
  overrides: Partial<platformApi.PlatformProvider> = {},
): platformApi.PlatformProvider {
  return {
    ...providersFixture[1],
    loaded_managed_model_id: null,
    loaded_managed_model_name: null,
    loaded_runtime_model_id: null,
    loaded_local_path: null,
    load_state: "empty",
    load_error: null,
    ...overrides,
  };
}

function buildProvidersList(
  embeddingsProvider: platformApi.PlatformProvider,
): platformApi.PlatformProvider[] {
  return [providersFixture[0], embeddingsProvider, providersFixture[2]];
}

describe("PlatformProviderDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    primePlatformControlMocks();
    vi.mocked(modelOpsModelsApi.listModelOpsModels).mockResolvedValue([localEmbeddingsModel]);
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

  it("shows validation failures in the shared action-feedback dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(platformApi.validatePlatformProvider).mockRejectedValue(
      new Error("Embeddings binding is missing a default resource"),
    );

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-1" },
    );

    await user.click(screen.getByRole("button", { name: await t("platformControl.actions.validate") }));

    await waitFor(() => {
      expect(platformApi.validatePlatformProvider).toHaveBeenCalledWith("provider-1", "token");
    });
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("Embeddings binding is missing a default resource")).toBeVisible();
  });

  it("opens the runtime load side panel immediately and keeps it non-dismissible while loading", async () => {
    const user = userEvent.setup();
    const loadPanelTitle = await t("platformControl.providers.loadPanelTitle");
    const loadingSummary = await t("platformControl.providers.loadPanelSummaryLoading", { name: localEmbeddingsModel.name });
    const loadingPhaseLabel = await t("platformControl.providers.loadPanelPhases.loading");
    const dismissLabel = await t("platformControl.providers.loadPanelDismiss");
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildProvidersList(buildEmbeddingsProvider()));
    vi.mocked(platformApi.assignPlatformProviderLoadedModel).mockResolvedValue(
      buildEmbeddingsProvider({
        loaded_managed_model_id: localEmbeddingsModel.id,
        loaded_managed_model_name: localEmbeddingsModel.name,
        load_state: "loading",
      }),
    );

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    await user.selectOptions(
      await screen.findByLabelText(await t("platformControl.providers.loadedModelSelectLabel")),
      localEmbeddingsModel.id,
    );
    await user.click(screen.getByRole("button", { name: await t("platformControl.actions.assignLoadedModel") }));

    await waitFor(() => {
      expect(platformApi.assignPlatformProviderLoadedModel).toHaveBeenCalledWith(
        "provider-embeddings",
        localEmbeddingsModel.id,
        "token",
      );
    });

    expect(await screen.findByRole("status", { name: loadPanelTitle })).toBeVisible();
    expect(screen.getByText(loadingSummary)).toBeVisible();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuetext",
      loadingPhaseLabel,
    );
    expect(screen.queryByRole("button", { name: dismissLabel })).not.toBeInTheDocument();
  });

  it("updates the side panel to success after the runtime reports the model as loaded", async () => {
    const user = userEvent.setup();
    const loadPanelTitle = await t("platformControl.providers.loadPanelTitle");
    const loadedSummary = await t("platformControl.providers.loadPanelSummaryLoaded", { name: localEmbeddingsModel.name });
    const dismissLabel = await t("platformControl.providers.loadPanelDismiss");
    const loadedStateHint = await t("platformControl.providers.loadedModelStateHintLoaded");
    vi.mocked(platformApi.listPlatformProviders)
      .mockResolvedValueOnce(buildProvidersList(buildEmbeddingsProvider()))
      .mockResolvedValueOnce(buildProvidersList(buildEmbeddingsProvider({
        loaded_managed_model_id: localEmbeddingsModel.id,
        loaded_managed_model_name: localEmbeddingsModel.name,
        loaded_runtime_model_id: "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
        load_state: "loaded",
      })));
    vi.mocked(platformApi.assignPlatformProviderLoadedModel).mockResolvedValue(
      buildEmbeddingsProvider({
        loaded_managed_model_id: localEmbeddingsModel.id,
        loaded_managed_model_name: localEmbeddingsModel.name,
        load_state: "loading",
      }),
    );

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    await user.selectOptions(
      await screen.findByLabelText(await t("platformControl.providers.loadedModelSelectLabel")),
      localEmbeddingsModel.id,
    );
    await user.click(screen.getByRole("button", { name: await t("platformControl.actions.assignLoadedModel") }));

    const panel = await screen.findByRole("status", { name: loadPanelTitle });
    expect(panel).toBeVisible();
    await waitFor(() => {
      expect(within(panel).getByText(loadedSummary)).toBeVisible();
    });
    expect(within(panel).getByText("/models/embeddings/sentence-transformers--all-MiniLM-L6-v2")).toBeVisible();
    expect(within(panel).getByText(loadedStateHint)).toBeVisible();
    expect(within(panel).queryByText("platformControl.providers.loadedModelStateHint")).not.toBeInTheDocument();
    expect(within(panel).queryByText(await t("platformControl.summary.none"))).not.toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: dismissLabel })).toBeVisible();
  });

  it("keeps the assigned model card compact when no runtime detail is available", async () => {
    const loadedModelTitle = await t("platformControl.providers.loadedModelTitle");
    const loadedStateHint = await t("platformControl.providers.loadedModelStateHintLoaded");
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildProvidersList(buildEmbeddingsProvider({
      loaded_managed_model_id: localEmbeddingsModel.id,
      loaded_managed_model_name: localEmbeddingsModel.name,
      load_state: "loaded",
    })));

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    const loadedModelSection = (await screen.findByRole("heading", { name: loadedModelTitle })).closest("article");
    expect(loadedModelSection).not.toBeNull();
    const loadedModelCard = within(loadedModelSection as HTMLElement).getByText(await t("platformControl.providers.loadedModelLabel")).closest(".platform-summary-card");
    expect(loadedModelCard).not.toBeNull();
    expect(within(loadedModelCard as HTMLElement).getByText(localEmbeddingsModel.name)).toBeVisible();
    expect(within(loadedModelCard as HTMLElement).queryByText(await t("platformControl.summary.none"))).not.toBeInTheDocument();
    expect(within(loadedModelSection as HTMLElement).getByText(loadedStateHint)).toBeVisible();
  });

  it("uses the runtime model as the only assigned-model line when no managed model is assigned", async () => {
    const loadedModelTitle = await t("platformControl.providers.loadedModelTitle");
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildProvidersList(buildEmbeddingsProvider({
      loaded_managed_model_id: null,
      loaded_managed_model_name: null,
      loaded_runtime_model_id: "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
      load_state: "loaded",
    })));

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    const loadedModelSection = (await screen.findByRole("heading", { name: loadedModelTitle })).closest("article");
    expect(loadedModelSection).not.toBeNull();
    const loadedModelCard = within(loadedModelSection as HTMLElement).getByText(await t("platformControl.providers.loadedModelLabel")).closest(".platform-summary-card");
    expect(loadedModelCard).not.toBeNull();
    expect(within(loadedModelCard as HTMLElement).getByText("/models/llm/Qwen--Qwen2.5-0.5B-Instruct")).toBeVisible();
    expect(within(loadedModelCard as HTMLElement).queryByText(await t("platformControl.summary.none"))).not.toBeInTheDocument();
  });

  it("shows runtime detail when a runtime model id exists and uses state-specific helper text", async () => {
    const loadedModelTitle = await t("platformControl.providers.loadedModelTitle");
    const loadedStateHint = await t("platformControl.providers.loadedModelStateHintLoaded");
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildProvidersList(buildEmbeddingsProvider({
      loaded_managed_model_id: localEmbeddingsModel.id,
      loaded_managed_model_name: localEmbeddingsModel.name,
      loaded_runtime_model_id: "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
      load_state: "loaded",
    })));

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    const loadedModelSection = (await screen.findByRole("heading", { name: loadedModelTitle })).closest("article");
    expect(loadedModelSection).not.toBeNull();
    expect(within(loadedModelSection as HTMLElement).getByText("/models/embeddings/sentence-transformers--all-MiniLM-L6-v2")).toBeVisible();
    expect(within(loadedModelSection as HTMLElement).getByText(loadedStateHint)).toBeVisible();
  });

  it("shows the empty-state helper text when no local model is assigned", async () => {
    const emptyStateHint = await t("platformControl.providers.loadedModelStateHintEmpty");
    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildProvidersList(buildEmbeddingsProvider({
      load_state: "empty",
    })));

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    expect(await screen.findByText(emptyStateHint)).toBeVisible();
  });

  it("shows runtime errors in the side panel when model loading fails", async () => {
    const user = userEvent.setup();
    const errorSummary = await t("platformControl.providers.loadPanelSummaryError", { name: localEmbeddingsModel.name });
    const dismissLabel = await t("platformControl.providers.loadPanelDismiss");
    const loadedModelTitle = await t("platformControl.providers.loadedModelTitle");
    vi.mocked(platformApi.listPlatformProviders)
      .mockResolvedValueOnce(buildProvidersList(buildEmbeddingsProvider()))
      .mockResolvedValueOnce(buildProvidersList(buildEmbeddingsProvider({
        loaded_managed_model_id: localEmbeddingsModel.id,
        loaded_managed_model_name: localEmbeddingsModel.name,
        load_state: "error",
        load_error: "GPU out of memory",
      })));
    vi.mocked(platformApi.assignPlatformProviderLoadedModel).mockResolvedValue(
      buildEmbeddingsProvider({
        loaded_managed_model_id: localEmbeddingsModel.id,
        loaded_managed_model_name: localEmbeddingsModel.name,
        load_state: "loading",
      }),
    );

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    await user.selectOptions(
      await screen.findByLabelText(await t("platformControl.providers.loadedModelSelectLabel")),
      localEmbeddingsModel.id,
    );
    await user.click(screen.getByRole("button", { name: await t("platformControl.actions.assignLoadedModel") }));

    const panel = await screen.findByRole("status", { name: await t("platformControl.providers.loadPanelTitle") });
    await waitFor(() => {
      expect(within(panel).getByText(errorSummary)).toBeVisible();
    });
    expect(within(panel).getByText("GPU out of memory")).toBeVisible();
    expect(within(panel).getByRole("button", { name: dismissLabel })).toBeVisible();
    const loadedModelSection = screen.getByRole("heading", { name: loadedModelTitle }).closest("article");
    expect(loadedModelSection).not.toBeNull();
    expect(within(loadedModelSection as HTMLElement).getByText("GPU out of memory")).toBeVisible();
  });

  it("restores the side panel across reloads and keeps dismissed terminal states closed", async () => {
    const loadPanelTitle = await t("platformControl.providers.loadPanelTitle");
    const dismissLabel = await t("platformControl.providers.loadPanelDismiss");
    const loadedModelTitle = await t("platformControl.providers.loadedModelTitle");
    const storedStatus = {
      providerId: "provider-embeddings",
      requestedModelId: localEmbeddingsModel.id,
      requestedModelName: localEmbeddingsModel.name,
      statusOpen: true,
      dismissedTerminalState: false,
    };
    window.sessionStorage.setItem(
      "vanessa:platform-provider-load:provider-embeddings",
      JSON.stringify(storedStatus),
    );

    vi.mocked(platformApi.listPlatformProviders).mockResolvedValue(buildProvidersList(buildEmbeddingsProvider({
      loaded_managed_model_id: localEmbeddingsModel.id,
      loaded_managed_model_name: localEmbeddingsModel.name,
      loaded_runtime_model_id: "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
      load_state: "loaded",
    })));

    const firstRender = await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    expect(await screen.findByRole("status", { name: loadPanelTitle })).toBeVisible();
    const loadedModelSection = screen.getByRole("heading", { name: loadedModelTitle }).closest("article");
    expect(loadedModelSection).not.toBeNull();
    expect(within(loadedModelSection as HTMLElement).getByText(localEmbeddingsModel.name)).toBeVisible();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: dismissLabel }));
    await waitFor(() => {
      expect(screen.queryByRole("status", { name: loadPanelTitle })).not.toBeInTheDocument();
    });
    expect(within(loadedModelSection as HTMLElement).getByText(localEmbeddingsModel.name)).toBeVisible();

    firstRender.unmount();

    await renderWithAppProviders(
      <Routes>
        <Route path="/control/platform/providers/:providerId" element={<PlatformProviderDetailPage />} />
      </Routes>,
      { route: "/control/platform/providers/provider-embeddings" },
    );

    expect(screen.queryByRole("status", { name: loadPanelTitle })).not.toBeInTheDocument();
  });
});
