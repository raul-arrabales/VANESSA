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
  listModelCatalog: vi.fn(),
  listModelAssignments: vi.fn(),
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
  discoverHfModels: vi.fn(),
  getHfModelDetails: vi.fn(),
  startModelDownload: vi.fn(),
  listDownloadJobs: vi.fn(),
}));

vi.mock("../api/models", () => ({
  listModelCatalog: modelApiMocks.listModelCatalog,
  listModelAssignments: modelApiMocks.listModelAssignments,
  createModelCatalogItem: modelApiMocks.createModelCatalogItem,
  updateModelAssignment: modelApiMocks.updateModelAssignment,
  discoverHfModels: modelApiMocks.discoverHfModels,
  getHfModelDetails: modelApiMocks.getHfModelDetails,
  startModelDownload: modelApiMocks.startModelDownload,
  listDownloadJobs: modelApiMocks.listDownloadJobs,
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
    modelApiMocks.listModelCatalog.mockResolvedValue([
      { id: "gpt-4", name: "GPT-4", model_type: "llm" },
      { id: "mistral-small", name: "Mistral Small", model_type: "llm" },
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
    await user.selectOptions(screen.getByLabelText("models.catalog.typeLabel"), "embedding");
    await user.click(screen.getByRole("button", { name: "models.catalog.addButton" }));
    expect(modelApiMocks.createModelCatalogItem).toHaveBeenCalledWith(
      { name: "New Model", provider: undefined, model_type: "embedding" },
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
    await user.selectOptions(screen.getByLabelText("models.discovery.typeLabel"), "embedding");
    await user.type(screen.getByLabelText("models.discovery.queryLabel"), "llama");
    await user.click(screen.getByRole("button", { name: "models.discovery.searchButton" }));

    expect(await screen.findByText("meta-llama/Llama-3-8B-Instruct")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "models.discovery.downloadButton" }));
    expect(modelApiMocks.startModelDownload).toHaveBeenCalledWith(
      expect.objectContaining({ source_id: "meta-llama/Llama-3-8B-Instruct", model_type: "embedding" }),
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
