import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LocalModelRegisterPage from "./LocalModelRegisterPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const localApiMocks = vi.hoisted(() => ({
  discoverHfModels: vi.fn(),
  getHfModelDetails: vi.fn(),
  listDownloadJobs: vi.fn(),
  startModelDownload: vi.fn(),
}));

const modelApiMocks = vi.hoisted(() => ({
  registerManagedModel: vi.fn(),
}));

vi.mock("../../../api/modelops/local", () => ({
  discoverHfModels: localApiMocks.discoverHfModels,
  getHfModelDetails: localApiMocks.getHfModelDetails,
  listDownloadJobs: localApiMocks.listDownloadJobs,
  startModelDownload: localApiMocks.startModelDownload,
}));

vi.mock("../../../api/modelops/models", () => ({
  registerManagedModel: modelApiMocks.registerManagedModel,
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
    modelApiMocks.registerManagedModel.mockResolvedValue({ id: "phi-local" });
  });

  it("shows offline Hugging Face search failures in the themed modal instead of inline text", async () => {
    localApiMocks.discoverHfModels.mockRejectedValueOnce(
      new Error("Model discovery disabled for runtime profile 'offline'"),
    );
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
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

    await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
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
    const view = await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
    await user.type(screen.getByLabelText("Model id"), "phi-local");
    await user.type(screen.getByLabelText("Model name"), "Phi Local");
    await user.click(screen.getByRole("button", { name: "Register local model" }));

    expect(await screen.findByRole("dialog", { name: "Manual local registration" })).toBeVisible();
    expect(screen.getByText("Manual registration failed for phi-local")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("shows manual registration success in the shared modal and keeps only one success message", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
    await user.type(screen.getByLabelText("Model id"), "phi-local");
    await user.type(screen.getByLabelText("Model name"), "Phi Local");
    await user.click(screen.getByRole("button", { name: "Register local model" }));

    expect(await screen.findByRole("dialog", { name: "Manual local registration" })).toBeVisible();
    expect(screen.getAllByText("Local model registered.")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Test model" })).toHaveAttribute("href", "/control/models/phi-local/test");
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
    const view = await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await user.click(await screen.findByRole("button", { name: "Inspect" }));

    expect(await screen.findByRole("dialog", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.getByText("Repository details are unavailable right now.")).toBeVisible();
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("keeps non-error discovery feedback inline when no models are found", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
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

    await renderWithAppProviders(<LocalModelRegisterPage />);

    await screen.findByRole("heading", { name: "Local model registration" });
    await user.click(screen.getByRole("button", { name: "Search Hugging Face" }));
    await user.click(await screen.findByRole("button", { name: "Download" }));

    expect(await screen.findByRole("dialog", { name: "Hugging Face discovery" })).toBeVisible();
    expect(screen.getAllByText("Started download for meta-llama/Llama-3-8B-Instruct.")).toHaveLength(1);
    expect(screen.queryByText("No models found for this query.")).not.toBeInTheDocument();
  });
});
