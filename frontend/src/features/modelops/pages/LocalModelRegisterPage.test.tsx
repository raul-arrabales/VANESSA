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

function buildDiscoveredModel(index: number) {
  return {
    source_id: `org/model-${index}`,
    name: `Model ${index}`,
    downloads: 100 - index,
    likes: index,
    tags: ["llm"],
    provider: "huggingface",
  };
}

describe("LocalModelRegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    localApiMocks.discoverHfModels.mockResolvedValue([]);
    localApiMocks.getHfModelDetails.mockResolvedValue({
      source_id: "meta-llama/Llama-3-8B-Instruct",
      name: "Llama 3 8B Instruct",
      sha: "abc123",
      downloads: 42,
      likes: 5,
      author: "meta-llama",
      pipeline_tag: "text-generation",
      library_name: "transformers",
      gated: "manual",
      private: false,
      disabled: false,
      last_modified: "2026-01-03T03:04:00+00:00",
      used_storage: 2048,
      files: [
        {
          path: "model.safetensors",
          size: 1024,
          file_type: "safetensors",
          blob_id: "blob-1",
          lfs: { oid: "sha256:abc", size: 1024 },
        },
        { path: "config.json", size: 256, file_type: "json" },
      ],
      tags: ["llm", "safetensors"],
      card_data: { license: "apache-2.0" },
      config: { model_type: "llama" },
      safetensors: { total: 1 },
      model_index: [{ name: "llama" }],
      transformers_info: { auto_model: "AutoModelForCausalLM" },
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

  it("scrolls to the top of the discovery results after a successful search", async () => {
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

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=discovery" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));

    expect(await screen.findByText("meta-llama/Llama-3-8B-Instruct")).toBeVisible();
    await waitFor(() => {
      expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalledWith({
        behavior: "smooth",
        block: "start",
      });
    });
  });

  it("loads an additional Hugging Face results batch and appends it to the list", async () => {
    localApiMocks.discoverHfModels
      .mockResolvedValueOnce(Array.from({ length: 12 }, (_item, index) => buildDiscoveredModel(index)))
      .mockResolvedValueOnce([
        buildDiscoveredModel(12),
        buildDiscoveredModel(13),
      ]);
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=discovery" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));

    expect(await screen.findByText("org/model-0")).toBeVisible();
    vi.mocked(HTMLElement.prototype.scrollIntoView).mockClear();
    await user.click(await screen.findByRole("button", { name: "Load more matches" }));

    expect(await screen.findByText("org/model-13")).toBeVisible();
    expect(screen.getByText("org/model-0")).toBeVisible();
    expect(screen.getByText("13.")).toBeVisible();
    expect(screen.getByText("14.")).toBeVisible();
    await waitFor(() => {
      expect(vi.mocked(HTMLElement.prototype.scrollIntoView).mock.contexts).toContainEqual(
        expect.objectContaining({
          dataset: expect.objectContaining({
            discoveryResultIndex: "12",
          }),
        }),
      );
    });
    expect(localApiMocks.discoverHfModels).toHaveBeenNthCalledWith(
      2,
      "token",
      expect.objectContaining({
        limit: 12,
        offset: 12,
      }),
    );
    expect(screen.queryByRole("button", { name: "Load more matches" })).not.toBeInTheDocument();
  });

  it("resets result numbering when a new Hugging Face search replaces the list", async () => {
    localApiMocks.discoverHfModels
      .mockResolvedValueOnce(Array.from({ length: 12 }, (_item, index) => buildDiscoveredModel(index)))
      .mockResolvedValueOnce([
        buildDiscoveredModel(12),
        buildDiscoveredModel(13),
      ])
      .mockResolvedValueOnce([
        {
          ...buildDiscoveredModel(99),
          source_id: "org/fresh-model",
          name: "Fresh Model",
        },
      ]);
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=discovery" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await user.click(await screen.findByRole("button", { name: "Load more matches" }));

    expect(await screen.findByText("14.")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));

    expect(await screen.findByText("org/fresh-model")).toBeVisible();
    expect(screen.getByText("1.")).toBeVisible();
    expect(screen.queryByText("14.")).not.toBeInTheDocument();
    expect(screen.queryByText("org/model-13")).not.toBeInTheDocument();
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

  it("renders local artifacts as a register-local subview", async () => {
    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=artifacts" });

    expect(await screen.findByRole("heading", { name: "Local artifacts" })).toBeVisible();
    expect(await screen.findByText("Phi Local")).toBeVisible();
    expect(screen.getByRole("link", { name: "Register local model" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Local artifacts" })).not.toBeInTheDocument();
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
    expect(screen.queryByRole("dialog", { name: "meta-llama/Llama-3-8B-Instruct" })).not.toBeInTheDocument();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("opens inspected Hugging Face model details in an app modal", async () => {
    localApiMocks.discoverHfModels.mockResolvedValueOnce([
      {
        source_id: "meta-llama/Llama-3-8B-Instruct",
        name: "Llama 3 8B Instruct",
        downloads: 42,
        likes: 5,
        tags: ["llm", "safetensors"],
        provider: "huggingface",
      },
    ]);
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />, { route: "/control/models/local/register?view=discovery" });

    await screen.findByRole("heading", { name: "Hugging Face discovery" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await user.click(await screen.findByRole("button", { name: "Inspect" }));

    const dialog = await screen.findByRole("dialog", { name: "meta-llama/Llama-3-8B-Instruct" });
    expect(dialog).toBeVisible();
    expect(localApiMocks.getHfModelDetails).toHaveBeenCalledWith("meta-llama/Llama-3-8B-Instruct", "token");
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
