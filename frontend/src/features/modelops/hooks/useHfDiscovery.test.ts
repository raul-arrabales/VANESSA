import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useHfDiscovery } from "./useHfDiscovery";

const localApiMocks = vi.hoisted(() => ({
  discoverHfModels: vi.fn(),
  getHfModelDetails: vi.fn(),
}));

const feedbackMocks = vi.hoisted(() => ({
  showErrorFeedback: vi.fn(),
}));

vi.mock("../../../api/modelops/local", () => ({
  discoverHfModels: localApiMocks.discoverHfModels,
  getHfModelDetails: localApiMocks.getHfModelDetails,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../../feedback/ActionFeedbackProvider", () => ({
  useActionFeedback: () => feedbackMocks,
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

describe("useHfDiscovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localApiMocks.discoverHfModels.mockResolvedValue([]);
    localApiMocks.getHfModelDetails.mockResolvedValue({
      source_id: "org/model-0",
      name: "Model 0",
      files: [],
      tags: [],
    });
  });

  it("searches, tracks load-more availability, and appends additional batches", async () => {
    localApiMocks.discoverHfModels
      .mockResolvedValueOnce(Array.from({ length: 12 }, (_item, index) => buildDiscoveredModel(index)))
      .mockResolvedValueOnce([buildDiscoveredModel(12)]);

    const { result } = renderHook(() => useHfDiscovery("token"));

    await act(async () => {
      await result.current.search({ query: "llama", task_key: "llm" });
    });

    expect(result.current.discoveredModels).toHaveLength(12);
    expect(result.current.canLoadMoreModels).toBe(true);
    expect(result.current.completedSearchId).toBe(1);

    await act(async () => {
      await result.current.loadMore({ query: "llama", task_key: "llm" });
    });

    expect(result.current.discoveredModels).toHaveLength(13);
    expect(result.current.discoveredModels[12].source_id).toBe("org/model-12");
    expect(result.current.canLoadMoreModels).toBe(false);
    expect(result.current.latestLoadedBatchStartIndex).toBe(12);
    expect(result.current.completedLoadMoreId).toBe(1);
    expect(localApiMocks.discoverHfModels).toHaveBeenNthCalledWith(
      2,
      "token",
      expect.objectContaining({
        offset: 12,
        limit: 12,
      }),
    );
  });

  it("shows empty feedback for empty searches and routes inspect failures through shared feedback", async () => {
    localApiMocks.getHfModelDetails.mockRejectedValueOnce(new Error("details unavailable"));
    const { result } = renderHook(() => useHfDiscovery("token"));

    await act(async () => {
      await result.current.search({ query: "missing", task_key: "embeddings" });
    });

    expect(result.current.feedback).toBe("models.discovery.empty");
    expect(localApiMocks.discoverHfModels).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({
        task: "feature-extraction",
      }),
    );

    let details = null;
    await act(async () => {
      details = await result.current.inspect("org/model-0");
    });

    expect(details).toBeNull();
    expect(feedbackMocks.showErrorFeedback).toHaveBeenCalledWith(
      expect.any(Error),
      "modelOps.local.inspectFailure",
      { titleKey: "modelOps.local.discoveryTitle" },
    );
  });
});
