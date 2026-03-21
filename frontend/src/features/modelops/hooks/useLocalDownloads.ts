import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  discoverHfModels,
  getHfModelDetails,
  listDownloadJobs,
  startModelDownload,
  type HfDiscoveredModel,
  type ModelDownloadJob,
} from "../../../api/models";

const ACTIVE_JOB_STATUSES = new Set(["queued", "running"]);
const BASE_POLL_INTERVAL_MS = 3000;
const BACKOFF_POLL_INTERVAL_MS = 5000;
const POLL_BACKOFF_AFTER_MS = 120_000;

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
  selectedModelInfo: string;
  downloadJobs: ModelDownloadJob[];
  hasActiveJobs: boolean;
  error: string;
  feedback: string;
  search: (params: { query: string; task_key: string }) => Promise<void>;
  inspect: (sourceId: string) => Promise<void>;
  download: (model: HfDiscoveredModel, taskKey: string, category?: "predictive" | "generative") => Promise<void>;
  refreshJobs: () => Promise<void>;
} {
  const [discoveredModels, setDiscoveredModels] = useState<HfDiscoveredModel[]>([]);
  const [selectedModelInfo, setSelectedModelInfo] = useState("");
  const [downloadJobs, setDownloadJobs] = useState<ModelDownloadJob[]>([]);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
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
    setError("");
    setFeedback("");
    try {
      const models = await discoverHfModels(token, {
        query: params.query,
        task_key: params.task_key,
        task: params.task_key === "embeddings" ? "feature-extraction" : "text-generation",
        sort: "downloads",
        limit: 12,
      });
      setDiscoveredModels(models);
      setSelectedModelInfo("");
      if (models.length === 0) {
        setFeedback("No models found for this query.");
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to search Hugging Face.");
    }
  }, [token]);

  const inspect = useCallback(async (sourceId: string): Promise<void> => {
    if (!token) {
      return;
    }
    setError("");
    try {
      const details = await getHfModelDetails(sourceId, token);
      setSelectedModelInfo(`${details.source_id} • ${details.files.length} files`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load model details.");
    }
  }, [token]);

  const download = useCallback(async (
    model: HfDiscoveredModel,
    taskKey: string,
    category?: "predictive" | "generative",
  ): Promise<void> => {
    if (!token) {
      return;
    }
    setError("");
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
      setFeedback(`Started download for ${model.source_id}.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to start download.");
    }
  }, [token]);

  return {
    discoveredModels,
    selectedModelInfo,
    downloadJobs,
    hasActiveJobs,
    error,
    feedback,
    search,
    inspect,
    download,
    refreshJobs,
  };
}
