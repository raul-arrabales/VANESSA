import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLocalDownloadJobs } from "./useLocalDownloadJobs";

const localApiMocks = vi.hoisted(() => ({
  listDownloadJobs: vi.fn(),
  startModelDownload: vi.fn(),
}));

const feedbackMocks = vi.hoisted(() => ({
  showErrorFeedback: vi.fn(),
  showSuccessFeedback: vi.fn(),
}));

vi.mock("../../../api/modelops/local", () => ({
  listDownloadJobs: localApiMocks.listDownloadJobs,
  startModelDownload: localApiMocks.startModelDownload,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, values?: Record<string, string>) => (
      values?.source ? `${key}:${values.source}` : key
    ),
  }),
}));

vi.mock("../../../feedback/ActionFeedbackProvider", () => ({
  useActionFeedback: () => feedbackMocks,
}));

describe("useLocalDownloadJobs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localApiMocks.listDownloadJobs.mockResolvedValue([]);
    localApiMocks.startModelDownload.mockResolvedValue({
      job_id: "job-1",
      provider: "huggingface",
      source_id: "org/model-0",
      target_dir: "/models/org/model-0",
      status: "queued",
    });
  });

  it("loads download jobs and derives active-job state", async () => {
    localApiMocks.listDownloadJobs.mockResolvedValueOnce([
      {
        job_id: "job-active",
        provider: "huggingface",
        source_id: "org/model-0",
        target_dir: "/models/org/model-0",
        status: "queued",
      },
    ]);

    const { result } = renderHook(() => useLocalDownloadJobs("token"));

    await waitFor(() => {
      expect(result.current.downloadJobs).toHaveLength(1);
    });
    expect(result.current.hasActiveJobs).toBe(true);
  });

  it("starts a model download and prepends the returned job", async () => {
    const { result } = renderHook(() => useLocalDownloadJobs("token"));

    await waitFor(() => {
      expect(localApiMocks.listDownloadJobs).toHaveBeenCalledWith("token");
    });
    await act(async () => {
      await result.current.download(
        {
          source_id: "org/model-0",
          name: "Model 0",
          downloads: 1,
          likes: 1,
          tags: ["llm"],
          provider: "huggingface",
        },
        "llm",
        "generative",
      );
    });

    expect(localApiMocks.startModelDownload).toHaveBeenCalledWith(
      {
        source_id: "org/model-0",
        name: "Model 0",
        task_key: "llm",
        category: "generative",
      },
      "token",
    );
    expect(result.current.downloadJobs[0].job_id).toBe("job-1");
    expect(feedbackMocks.showSuccessFeedback).toHaveBeenCalledWith(
      "models.feedback.downloadStarted:org/model-0",
      { titleKey: "modelOps.local.discoveryTitle" },
    );
  });
});
