import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  discoverHfModels,
  getHfModelDetails,
} from "../../../api/modelops/local";
import type { HfDiscoveredModel, HfModelDetails } from "../../../api/modelops/types";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

const HF_DISCOVERY_BATCH_SIZE = 12;

type DiscoveryParams = {
  query: string;
  task_key: string;
};

function discoveryTaskForTaskKey(taskKey: string): string {
  return taskKey === "embeddings" ? "feature-extraction" : "text-generation";
}

export function useHfDiscovery(token: string): {
  discoveredModels: HfDiscoveredModel[];
  completedSearchId: number;
  completedLoadMoreId: number;
  latestLoadedBatchStartIndex: number | null;
  canLoadMoreModels: boolean;
  isLoadingMoreModels: boolean;
  feedback: string;
  search: (params: DiscoveryParams) => Promise<void>;
  loadMore: (params: DiscoveryParams) => Promise<void>;
  inspect: (sourceId: string) => Promise<HfModelDetails | null>;
  clearFeedback: () => void;
} {
  const [discoveredModels, setDiscoveredModels] = useState<HfDiscoveredModel[]>([]);
  const [feedback, setFeedback] = useState("");
  const [completedSearchId, setCompletedSearchId] = useState(0);
  const [completedLoadMoreId, setCompletedLoadMoreId] = useState(0);
  const [latestLoadedBatchStartIndex, setLatestLoadedBatchStartIndex] = useState<number | null>(null);
  const [canLoadMoreModels, setCanLoadMoreModels] = useState(false);
  const [isLoadingMoreModels, setIsLoadingMoreModels] = useState(false);
  const { t } = useTranslation("common");
  const { showErrorFeedback } = useActionFeedback();

  const clearFeedback = useCallback((): void => {
    setFeedback("");
  }, []);

  const search = useCallback(async (params: DiscoveryParams): Promise<void> => {
    if (!token) {
      return;
    }
    setFeedback("");
    try {
      const models = await discoverHfModels(token, {
        query: params.query,
        task_key: params.task_key,
        task: discoveryTaskForTaskKey(params.task_key),
        sort: "downloads",
        limit: HF_DISCOVERY_BATCH_SIZE,
      });
      setDiscoveredModels(models);
      setCanLoadMoreModels(models.length === HF_DISCOVERY_BATCH_SIZE);
      setIsLoadingMoreModels(false);
      setLatestLoadedBatchStartIndex(null);
      if (models.length > 0) {
        setCompletedSearchId((current) => current + 1);
      }
      if (models.length === 0) {
        setFeedback(t("models.discovery.empty"));
      }
    } catch (requestError) {
      showErrorFeedback(requestError, t("models.feedback.discoveryFailed"), {
        titleKey: "modelOps.local.discoveryTitle",
      });
    }
  }, [showErrorFeedback, t, token]);

  const loadMore = useCallback(async (params: DiscoveryParams): Promise<void> => {
    if (!token || isLoadingMoreModels) {
      return;
    }
    setFeedback("");
    setIsLoadingMoreModels(true);
    const offset = discoveredModels.length;
    try {
      const models = await discoverHfModels(token, {
        query: params.query,
        task_key: params.task_key,
        task: discoveryTaskForTaskKey(params.task_key),
        sort: "downloads",
        limit: HF_DISCOVERY_BATCH_SIZE,
        offset,
      });
      setDiscoveredModels((current) => [...current, ...models]);
      setCanLoadMoreModels(models.length === HF_DISCOVERY_BATCH_SIZE);
      if (models.length > 0) {
        setLatestLoadedBatchStartIndex(offset);
        setCompletedLoadMoreId((current) => current + 1);
      }
    } catch (requestError) {
      showErrorFeedback(requestError, t("models.feedback.discoveryFailed"), {
        titleKey: "modelOps.local.discoveryTitle",
      });
    } finally {
      setIsLoadingMoreModels(false);
    }
  }, [discoveredModels.length, isLoadingMoreModels, showErrorFeedback, t, token]);

  const inspect = useCallback(async (sourceId: string): Promise<HfModelDetails | null> => {
    if (!token) {
      return null;
    }
    try {
      return await getHfModelDetails(sourceId, token);
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.local.inspectFailure"), {
        titleKey: "modelOps.local.discoveryTitle",
      });
      return null;
    }
  }, [showErrorFeedback, t, token]);

  return {
    discoveredModels,
    completedSearchId,
    completedLoadMoreId,
    latestLoadedBatchStartIndex,
    canLoadMoreModels,
    isLoadingMoreModels,
    feedback,
    search,
    loadMore,
    inspect,
    clearFeedback,
  };
}
