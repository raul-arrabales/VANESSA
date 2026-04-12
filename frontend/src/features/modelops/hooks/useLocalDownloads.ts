import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  discoverHfModels,
  getHfModelDetails,
  listDownloadJobs,
  startModelDownload,
} from "../../../api/modelops/local";
import type { HfDiscoveredModel, HfModelDetails, ModelDownloadJob } from "../../../api/modelops/types";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

const ACTIVE_JOB_STATUSES = new Set(["queued", "running"]);
const BASE_POLL_INTERVAL_MS = 3000;
const BACKOFF_POLL_INTERVAL_MS = 5000;
const POLL_BACKOFF_AFTER_MS = 120_000;
const HF_DISCOVERY_BATCH_SIZE = 12;

function mergeActiveJobs(currentJobs: ModelDownloadJob[], activeJobs: ModelDownloadJob[]): ModelDownloadJob[] {
  const activeById = new Map(activeJobs.map((job) => [job.job_id, job]));
  const seen = new Set<string>();
  const merged = currentJobs.map((job) => {
    const next = activeById.get(job.job_id);
    if (next) {
      seen.add(job.job_id);
      return next;
    }
    return job;
  });
  return [...activeJobs.filter((job) => !seen.has(job.job_id)), ...merged];
}

export function useLocalDownloads(token: string): {
  discoveredModels: HfDiscoveredModel[];
  downloadJobs: ModelDownloadJob[];
  hasActiveJobs: boolean;
  completedSearchId: number;
  completedLoadMoreId: number;
  latestLoadedBatchStartIndex: number | null;
  canLoadMoreModels: boolean;
  isLoadingMoreModels: boolean;
  feedback: string;
  search: (params: { query: string; task_key: string }) => Promise<void>;
  loadMore: (params: { query: string; task_key: string }) => Promise<void>;
  inspect: (sourceId: string) => Promise<HfModelDetails | null>;
  download: (model: HfDiscoveredModel, taskKey: string, category?: "predictive" | "generative") => Promise<void>;
  refreshJobs: () => Promise<void>;
} {
  const [discoveredModels, setDiscoveredModels] = useState<HfDiscoveredModel[]>([]);
  const [downloadJobs, setDownloadJobs] = useState<ModelDownloadJob[]>([]);
  const [feedback, setFeedback] = useState("");
  const [completedSearchId, setCompletedSearchId] = useState(0);
  const [completedLoadMoreId, setCompletedLoadMoreId] = useState(0);
  const [latestLoadedBatchStartIndex, setLatestLoadedBatchStartIndex] = useState<number | null>(null);
  const [canLoadMoreModels, setCanLoadMoreModels] = useState(false);
  const [isLoadingMoreModels, setIsLoadingMoreModels] = useState(false);
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const jobsRef = useRef<ModelDownloadJob[]>([]);
  const pollingStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    jobsRef.current = downloadJobs;
  }, [downloadJobs]);

  const hasActiveJobs = useMemo(
    () => downloadJobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status)),
    [downloadJobs],
  );

  const refreshJobs = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }
    const jobs = await listDownloadJobs(token);
    setDownloadJobs(Array.isArray(jobs) ? jobs : []);
  }, [token]);

  useEffect(() => {
    void refreshJobs().catch(() => {});
  }, [refreshJobs]);

  useEffect(() => {
    if (!hasActiveJobs) {
      pollingStartedAtRef.current = null;
      return;
    }
    if (pollingStartedAtRef.current === null) {
      pollingStartedAtRef.current = Date.now();
    }
  }, [hasActiveJobs]);

  useEffect(() => {
    if (!token || !hasActiveJobs) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | undefined;

    const schedule = (): void => {
      if (cancelled) {
        return;
      }
      const startedAt = pollingStartedAtRef.current ?? Date.now();
      const elapsed = Date.now() - startedAt;
      const delay = elapsed >= POLL_BACKOFF_AFTER_MS ? BACKOFF_POLL_INTERVAL_MS : BASE_POLL_INTERVAL_MS;
      timeoutId = window.setTimeout(() => {
        void poll();
      }, delay);
    };

    const poll = async (): Promise<void> => {
      let continuePolling = true;
      try {
        const previousJobs = jobsRef.current;
        const [queuedJobs, runningJobs] = await Promise.all([
          listDownloadJobs(token, "queued"),
          listDownloadJobs(token, "running"),
        ]);
        const activeJobs = [...runningJobs, ...queuedJobs];
        const nextJobs = mergeActiveJobs(previousJobs, activeJobs);
        if (!cancelled) {
          setDownloadJobs(nextJobs);
          continuePolling = nextJobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status));
        }
      } catch {
        continuePolling = true;
      } finally {
        if (continuePolling) {
          schedule();
        }
      }
    };

    schedule();
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [hasActiveJobs, token]);

  const search = useCallback(async (params: { query: string; task_key: string }): Promise<void> => {
    if (!token) {
      return;
    }
    setFeedback("");
    try {
      const models = await discoverHfModels(token, {
        query: params.query,
        task_key: params.task_key,
        task: params.task_key === "embeddings" ? "feature-extraction" : "text-generation",
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

  const loadMore = useCallback(async (params: { query: string; task_key: string }): Promise<void> => {
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
        task: params.task_key === "embeddings" ? "feature-extraction" : "text-generation",
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

  const download = useCallback(async (
    model: HfDiscoveredModel,
    taskKey: string,
    category?: "predictive" | "generative",
  ): Promise<void> => {
    if (!token) {
      return;
    }
    setFeedback("");
    try {
      const job = await startModelDownload(
        {
          source_id: model.source_id,
          name: model.name,
          task_key: taskKey,
          category,
        },
        token,
      );
      setDownloadJobs((current) => [job, ...current]);
      showSuccessFeedback(t("models.feedback.downloadStarted", { source: model.source_id }), {
        titleKey: "modelOps.local.discoveryTitle",
      });
    } catch (requestError) {
      showErrorFeedback(requestError, t("models.feedback.downloadStartFailed"), {
        titleKey: "modelOps.local.discoveryTitle",
      });
    }
  }, [showErrorFeedback, showSuccessFeedback, t, token]);

  return {
    discoveredModels,
    downloadJobs,
    hasActiveJobs,
    completedSearchId,
    completedLoadMoreId,
    latestLoadedBatchStartIndex,
    canLoadMoreModels,
    isLoadingMoreModels,
    feedback,
    search,
    loadMore,
    inspect,
    download,
    refreshJobs,
  };
}
