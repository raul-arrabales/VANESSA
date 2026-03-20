import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SuperAdminModelsPage from "./SuperAdminModelsPage";
import TestRouter from "../test/TestRouter";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const modelApiMocks = vi.hoisted(() => ({
  listModelOpsModels: vi.fn(),
  listModelAssignments: vi.fn(),
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
  discoverHfModels: vi.fn(),
  getHfModelDetails: vi.fn(),
  startModelDownload: vi.fn(),
  listDownloadJobs: vi.fn(),
  validateManagedModel: vi.fn(),
  activateManagedModel: vi.fn(),
  deactivateManagedModel: vi.fn(),
  unregisterManagedModel: vi.fn(),
  deleteManagedModel: vi.fn(),
}));

vi.mock("../api/models", () => ({
  listModelOpsModels: modelApiMocks.listModelOpsModels,
  listModelAssignments: modelApiMocks.listModelAssignments,
  createModelCatalogItem: modelApiMocks.createModelCatalogItem,
  updateModelAssignment: modelApiMocks.updateModelAssignment,
  discoverHfModels: modelApiMocks.discoverHfModels,
  getHfModelDetails: modelApiMocks.getHfModelDetails,
  startModelDownload: modelApiMocks.startModelDownload,
  listDownloadJobs: modelApiMocks.listDownloadJobs,
  validateManagedModel: modelApiMocks.validateManagedModel,
  activateManagedModel: modelApiMocks.activateManagedModel,
  deactivateManagedModel: modelApiMocks.deactivateManagedModel,
  unregisterManagedModel: modelApiMocks.unregisterManagedModel,
  deleteManagedModel: modelApiMocks.deleteManagedModel,
}));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    },
    token: "token",
  }),
}));

describe("SuperAdminModelsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.listModelOpsModels.mockResolvedValue([
      { id: "gpt-4", name: "GPT-4", task_key: "llm", category: "generative", lifecycle_state: "registered", is_validation_current: false, usage_summary: { total_requests: 0 } },
      { id: "mistral-small", name: "Mistral Small", task_key: "llm", category: "generative", lifecycle_state: "active", is_validation_current: true, last_validation_status: "success", usage_summary: { total_requests: 3 } },
    ]);
    modelApiMocks.listModelAssignments.mockResolvedValue([
      { scope: "user", model_ids: ["mistral-small"] },
      { scope: "admin", model_ids: ["gpt-4"] },
      { scope: "superadmin", model_ids: ["gpt-4"] },
    ]);
    modelApiMocks.listDownloadJobs.mockResolvedValue([]);
    modelApiMocks.discoverHfModels.mockResolvedValue([]);
    modelApiMocks.getHfModelDetails.mockResolvedValue({ source_id: "hf/model", name: "model", files: [] });
    modelApiMocks.startModelDownload.mockResolvedValue({
      job_id: "job-1",
      provider: "huggingface",
      source_id: "hf/model",
      target_dir: "/models/llm/hf--model",
      status: "queued",
    });
    modelApiMocks.validateManagedModel.mockResolvedValue({});
    modelApiMocks.activateManagedModel.mockResolvedValue({});
    modelApiMocks.deactivateManagedModel.mockResolvedValue({});
    modelApiMocks.unregisterManagedModel.mockResolvedValue({});
    modelApiMocks.deleteManagedModel.mockResolvedValue({});
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders catalog and assignment controls", async () => {
    render(
      <TestRouter>
        <SuperAdminModelsPage />
      </TestRouter>,
    );

    expect(await screen.findByRole("heading", { name: "models.catalog.title" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "models.assignments.title" })).toBeVisible();
    expect(screen.getByLabelText("models.catalog.nameLabel")).toBeVisible();
    expect(screen.getByLabelText("user model scope")).toBeVisible();
  });

  it("creates catalog item and updates assignments", async () => {
    const user = userEvent.setup();
    modelApiMocks.createModelCatalogItem.mockResolvedValue({ id: "new-model", name: "New Model" });
    modelApiMocks.updateModelAssignment.mockResolvedValue({ scope: "user", model_ids: ["mistral-small", "gpt-4"] });

    render(
      <TestRouter>
        <SuperAdminModelsPage />
      </TestRouter>,
    );

    await screen.findByRole("heading", { name: "models.catalog.title" });

    await user.type(screen.getByLabelText("models.catalog.nameLabel"), "New Model");
    await user.selectOptions(screen.getByLabelText("models.catalog.typeLabel"), "embeddings");
    await user.click(screen.getByRole("button", { name: "models.catalog.addButton" }));
    expect(modelApiMocks.createModelCatalogItem).toHaveBeenCalledWith(
      { name: "New Model", provider: undefined, task_key: "embeddings", category: "predictive" },
      "token",
    );

    const gptCheckbox = screen.getAllByRole("checkbox")[0];
    await user.click(gptCheckbox);
    expect(modelApiMocks.updateModelAssignment).toHaveBeenCalled();
  });

  it("searches and starts download job from discovery list", async () => {
    const user = userEvent.setup();
    modelApiMocks.discoverHfModels.mockResolvedValueOnce([
      { source_id: "meta-llama/Llama-3-8B-Instruct", name: "Llama-3-8B-Instruct", tags: [], provider: "huggingface", downloads: 1000 },
    ]);

    render(
      <TestRouter>
        <SuperAdminModelsPage />
      </TestRouter>,
    );

    await screen.findByRole("heading", { name: "models.catalog.title" });
    await user.selectOptions(screen.getByLabelText("models.discovery.typeLabel"), "embeddings");
    await user.type(screen.getByLabelText("models.discovery.queryLabel"), "llama");
    await user.click(screen.getByRole("button", { name: "models.discovery.searchButton" }));

    expect(await screen.findByText("meta-llama/Llama-3-8B-Instruct")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "models.discovery.downloadButton" }));
    expect(modelApiMocks.startModelDownload).toHaveBeenCalledWith(
      expect.objectContaining({ source_id: "meta-llama/Llama-3-8B-Instruct", task_key: "embeddings", category: "predictive" }),
      "token",
    );
  });

  it("does not poll when there are no active jobs", async () => {
    vi.useFakeTimers();
    render(
      <TestRouter>
        <SuperAdminModelsPage />
      </TestRouter>,
    );

    expect(screen.getByRole("heading", { name: "models.catalog.title" })).toBeVisible();
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(12_000);
    });

    expect(modelApiMocks.listDownloadJobs).toHaveBeenCalledWith("token");
    const statusPollCalls = modelApiMocks.listDownloadJobs.mock.calls.filter(
      (call) => call[1] === "queued" || call[1] === "running",
    );
    expect(statusPollCalls.length).toBe(0);
    expect(screen.getByText("models.jobs.noActive")).toBeVisible();
  });

  it("shows active polling status when there are running jobs", async () => {
    const runningJob = {
      job_id: "job-1",
      provider: "huggingface",
      source_id: "hf/model",
      target_dir: "/models/llm/hf--model",
      status: "running",
    };

    modelApiMocks.listDownloadJobs.mockReset();
    modelApiMocks.listDownloadJobs.mockResolvedValue([runningJob]);

    render(
      <TestRouter>
        <SuperAdminModelsPage />
      </TestRouter>,
    );

    expect(await screen.findByText("models.jobs.pollingActive")).toBeVisible();
  });
});
