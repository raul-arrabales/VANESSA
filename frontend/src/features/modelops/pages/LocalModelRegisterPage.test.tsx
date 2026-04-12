import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LocalModelRegisterPage from "./LocalModelRegisterPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const localApiMocks = vi.hoisted(() => ({
  discoverHfModels: vi.fn(),
  getHfModelDetails: vi.fn(),
  listDownloadJobs: vi.fn(),
  startModelDownload: vi.fn(),
  listLocalModelArtifacts: vi.fn(),
}));

const modelApiMocks = vi.hoisted(() => ({
  registerManagedModel: vi.fn(),
  registerExistingManagedModel: vi.fn(),
}));

vi.mock("../../../api/modelops/local", () => ({
  discoverHfModels: localApiMocks.discoverHfModels,
  getHfModelDetails: localApiMocks.getHfModelDetails,
  listDownloadJobs: localApiMocks.listDownloadJobs,
  startModelDownload: localApiMocks.startModelDownload,
  listLocalModelArtifacts: localApiMocks.listLocalModelArtifacts,
}));

vi.mock("../../../api/modelops/models", () => ({
  registerManagedModel: modelApiMocks.registerManagedModel,
  registerExistingManagedModel: modelApiMocks.registerExistingManagedModel,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "superadmin", email: "sa@example.com", role: "superadmin", is_active: true },
    token: "token",
    isAuthenticated: true,
  }),
}));

describe("LocalModelRegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localApiMocks.discoverHfModels.mockResolvedValue([]);
    localApiMocks.getHfModelDetails.mockResolvedValue({
      source_id: "meta-llama/Llama-3-8B-Instruct",
      name: "Llama 3 8B Instruct",
      files: [],
      tags: ["llm"],
    });
    localApiMocks.listDownloadJobs.mockResolvedValue([]);
    localApiMocks.startModelDownload.mockResolvedValue({
      job_id: "job-1",
      provider: "huggingface",
      source_id: "meta-llama/Llama-3-8B-Instruct",
      target_dir: "/models/meta-llama/Llama-3-8B-Instruct",
      status: "queued",
    });
    localApiMocks.listLocalModelArtifacts.mockResolvedValue([
      {
        artifact_id: "artifact-1",
        suggested_model_id: "phi-local",
        name: "Phi Local",
        storage_path: "/models/phi-local",
        task_key: "llm",
        artifact_status: "ready",
        lifecycle_state: "downloaded",
        validation_hint: "ready",
        ready_for_registration: true,
      },
    ]);
    modelApiMocks.registerManagedModel.mockResolvedValue({ id: "phi-local" });
    modelApiMocks.registerExistingManagedModel.mockResolvedValue({ id: "phi-local" });
  });

  it("defaults to the discovery view and shows offline Hugging Face search failures in the themed modal", async () => {
    localApiMocks.discoverHfModels.mockRejectedValueOnce(
      new Error("Model discovery disabled for runtime profile 'offline'"),
    );
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    expect(screen.getByRole("link", { name: "Register local model" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Local artifacts" })).not.toBeInTheDocument();
    const viewNav = screen.getByRole("navigation", { name: "Local model registration sections" });
    expect(within(viewNav).getByRole("button", { name: "Hugging Face discovery" })).toHaveAttribute("aria-pressed", "true");
    expect(within(viewNav).getByRole("button", { name: "Active downloads" })).toBeVisible();
    expect(within(viewNav).getByRole("button", { name: "Manual registration" })).toBeVisible();
    expect(within(viewNav).getByRole("button", { name: "Local artifacts" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Active downloads" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Manual local registration" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Local artifacts" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));

    expect(await screen.findByRole("dialog", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.getByText("Model discovery disabled for runtime profile 'offline'")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("lets the user dismiss the shared error modal cleanly", async () => {
    localApiMocks.discoverHfModels.mockRejectedValueOnce(
      new Error("Model discovery disabled for runtime profile 'offline'"),
    );
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await screen.findByRole("dialog", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Close" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Hugging Face discovery" })).not.toBeInTheDocument();
    });
  });

  it("shows manual registration failures in the shared modal instead of inline text", async () => {
    modelApiMocks.registerManagedModel.mockRejectedValueOnce(
      new Error("Manual registration failed for phi-local"),
    );
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Manual registration" }));
    await screen.findByRole("heading", { name: "Manual local registration" });
    await user.type(screen.getByLabelText("Model id"), "phi-local");
    await user.type(screen.getByLabelText("Model name"), "Phi Local");
    await user.click(screen.getByRole("button", { name: "Register local model" }));

    expect(await screen.findByRole("dialog", { name: "Manual local registration" })).toBeVisible();
    expect(screen.getByText("Manual registration failed for phi-local")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("shows manual registration success in the shared modal and keeps only one success message", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Manual registration" }));
    await screen.findByRole("heading", { name: "Manual local registration" });
    await user.type(screen.getByLabelText("Model id"), "phi-local");
    await user.type(screen.getByLabelText("Model name"), "Phi Local");
    await user.click(screen.getByRole("button", { name: "Register local model" }));

    expect(await screen.findByRole("dialog", { name: "Manual local registration" })).toBeVisible();
    expect(screen.getAllByText("Local model registered.")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Test model" })).toHaveAttribute("href", "/control/models/phi-local/test");
  });

  it("switches between URL-driven local model views", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    const viewNav = await screen.findByRole("navigation", { name: "Local model registration sections" });
    await user.click(within(viewNav).getByRole("button", { name: "Active downloads" }));
    expect(within(viewNav).getByRole("button", { name: "Active downloads" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Active downloads" })).toBeVisible();
    expect(screen.getByText("No active downloads.")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Hugging Face discovery" })).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: "Manual registration" }));
    expect(within(viewNav).getByRole("button", { name: "Manual registration" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Manual local registration" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Hugging Face discovery" })).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: "Local artifacts" }));
    expect(within(viewNav).getByRole("button", { name: "Local artifacts" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Local artifacts" })).toBeVisible();
    expect(await screen.findByText("Phi Local")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Manual local registration" })).not.toBeInTheDocument();

    await user.click(within(viewNav).getByRole("button", { name: "Hugging Face discovery" }));
    expect(within(viewNav).getByRole("button", { name: "Hugging Face discovery" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Local artifacts" })).not.toBeInTheDocument();
  });

  it("falls back to discovery for invalid local model views", async () => {
    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=unknown" });

    expect(await screen.findByRole("heading", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Active downloads" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Manual local registration" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Local artifacts" })).not.toBeInTheDocument();
  });

  it("renders active downloads as a dedicated register-local subview", async () => {
    localApiMocks.listDownloadJobs.mockResolvedValueOnce([
      {
        job_id: "job-active",
        provider: "huggingface",
        source_id: "meta-llama/Llama-3-8B-Instruct",
        target_dir: "/models/meta-llama/Llama-3-8B-Instruct",
        status: "queued",
      },
    ]);

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=downloads" });

    expect(await screen.findByRole("heading", { name: "Active downloads" })).toBeVisible();
    expect(screen.getByText("Polling active downloads.")).toBeVisible();
    expect(screen.getByText("meta-llama/Llama-3-8B-Instruct · queued")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Hugging Face discovery" })).not.toBeInTheDocument();
  });

  it("renders local artifacts as a register-local subview and registers ready artifacts", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=artifacts" });

    expect(await screen.findByRole("heading", { name: "Local artifacts" })).toBeVisible();
    expect(await screen.findByText("Phi Local")).toBeVisible();
    expect(screen.getByRole("link", { name: "Register local model" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Local artifacts" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(modelApiMocks.registerExistingManagedModel).toHaveBeenCalledWith("phi-local", "token");
    expect(await screen.findByText("Artifact registered successfully.")).toBeVisible();
  });

  it("routes inspect failures through the themed discovery modal", async () => {
    localApiMocks.discoverHfModels.mockResolvedValueOnce([
      {
        source_id: "meta-llama/Llama-3-8B-Instruct",
        name: "Llama 3 8B Instruct",
        downloads: 42,
        likes: 5,
        tags: ["llm"],
        provider: "huggingface",
      },
    ]);
    localApiMocks.getHfModelDetails.mockRejectedValueOnce(
      new Error("Repository details are unavailable right now."),
    );
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await user.click(await screen.findByRole("button", { name: "Inspect" }));

    expect(await screen.findByRole("dialog", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.getByText("Repository details are unavailable right now.")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("keeps non-error discovery feedback inline when no models are found", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));

    expect(await screen.findByText("No models found for this query.")).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows download starts in the shared modal while keeping discovery empty-state feedback inline only", async () => {
    localApiMocks.discoverHfModels.mockResolvedValueOnce([
      {
        source_id: "meta-llama/Llama-3-8B-Instruct",
        name: "Llama 3 8B Instruct",
        downloads: 42,
        likes: 5,
        tags: ["llm"],
        provider: "huggingface",
      },
    ]);
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await user.click(await screen.findByRole("button", { name: "Download" }));

    expect(await screen.findByRole("dialog", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.getAllByText("Started download for meta-llama/Llama-3-8B-Instruct.")).toHaveLength(1);
    expect(screen.queryByText("No models found for this query.")).not.toBeInTheDocument();
  });
});
