import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import {
  createModelCatalogItem,
  discoverHfModels,
  getHfModelDetails,
  listDownloadJobs,
  listModelAssignments,
  listModelCatalog,
  startModelDownload,
  updateModelAssignment,
  type HfDiscoveredModel,
  type ModelDownloadJob,
  type ModelCatalogItem,
  type ModelScopeAssignment,
} from "../api/models";

const scopeOrder = ["user", "admin", "superadmin"];
const activeJobStatuses = new Set(["queued", "running"]);
const basePollIntervalMs = 3000;
const backoffPollIntervalMs = 5000;
const pollBackoffAfterMs = 120_000;

function mergeActiveJobs(
  currentJobs: ModelDownloadJob[],
  activeJobs: ModelDownloadJob[],
): ModelDownloadJob[] {
  const activeById = new Map(activeJobs.map((job) => [job.job_id, job]));
  const seen = new Set<string>();
  const mergedExisting = currentJobs.map((job) => {
    const refreshed = activeById.get(job.job_id);
    if (refreshed) {
      seen.add(job.job_id);
      return refreshed;
    }
    return job;
  });
  const newActive = activeJobs.filter((job) => !seen.has(job.job_id));
  return [...newActive, ...mergedExisting];
}

export default function SuperAdminModelsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();

  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [assignments, setAssignments] = useState<ModelScopeAssignment[]>([]);
  const [newModelName, setNewModelName] = useState("");
  const [newModelProvider, setNewModelProvider] = useState("");
  const [catalogModelType, setCatalogModelType] = useState<"llm" | "embedding">("llm");
  const [feedback, setFeedback] = useState("");
  const [discoverQuery, setDiscoverQuery] = useState("");
  const [discoveryModelType, setDiscoveryModelType] = useState<"llm" | "embedding">("llm");
  const [discoveredModels, setDiscoveredModels] = useState<HfDiscoveredModel[]>([]);
  const [selectedModelInfo, setSelectedModelInfo] = useState<string>("");
  const [downloadJobs, setDownloadJobs] = useState<ModelDownloadJob[]>([]);
  const downloadJobsRef = useRef<ModelDownloadJob[]>([]);
  const pollingStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    downloadJobsRef.current = downloadJobs;
  }, [downloadJobs]);

  const hasActiveJobs = useMemo(
    () => downloadJobs.some((job) => activeJobStatuses.has(job.status)),
    [downloadJobs],
  );

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

    const scheduleNextPoll = (): void => {
      if (cancelled) {
        return;
      }
      const startedAt = pollingStartedAtRef.current ?? Date.now();
      const elapsed = Date.now() - startedAt;
      const delay = elapsed >= pollBackoffAfterMs ? backoffPollIntervalMs : basePollIntervalMs;
      timeoutId = window.setTimeout(() => {
        void pollDownloads();
      }, delay);
    };

    const pollDownloads = async (): Promise<void> => {
      let shouldContinuePolling = true;
      try {
        const previousJobs = downloadJobsRef.current;
        const previousById = new Map(previousJobs.map((job) => [job.job_id, job]));
        const previousActiveIds = new Set(
          previousJobs.filter((job) => activeJobStatuses.has(job.status)).map((job) => job.job_id),
        );

        const [queuedJobsResult, runningJobsResult] = await Promise.all([
          listDownloadJobs(token, "queued"),
          listDownloadJobs(token, "running"),
        ]);
        const queuedJobs = Array.isArray(queuedJobsResult) ? queuedJobsResult : [];
        const runningJobs = Array.isArray(runningJobsResult) ? runningJobsResult : [];
        const activeJobs = [...runningJobs, ...queuedJobs];
        const activeIds = new Set(activeJobs.map((job) => job.job_id));
        const completedJobIds = Array.from(previousActiveIds).filter((id) => !activeIds.has(id));

        let nextJobs = mergeActiveJobs(previousJobs, activeJobs);
        let refreshCatalog = false;

        if (completedJobIds.length > 0) {
          const fullJobsResult = await listDownloadJobs(token);
          const fullJobs = Array.isArray(fullJobsResult) ? fullJobsResult : [];
          const nextById = new Map(fullJobs.map((job) => [job.job_id, job]));
          refreshCatalog = completedJobIds.some((id) => {
            const previous = previousById.get(id);
            const next = nextById.get(id);
            return previous !== undefined && next?.status === "succeeded";
          });
          nextJobs = fullJobs;
        }

        if (cancelled) {
          return;
        }
        setDownloadJobs(nextJobs);
        shouldContinuePolling = nextJobs.some((job) => activeJobStatuses.has(job.status));
        if (refreshCatalog) {
          void listModelCatalog(token).then(setModels).catch(() => {});
        }
      } catch {
        // Polling errors are non-fatal; continue polling while there are active jobs.
      } finally {
        if (shouldContinuePolling) {
          scheduleNextPoll();
        }
      }
    };

    scheduleNextPoll();
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [hasActiveJobs, token]);

  useEffect(() => {
    if (!token || !user) {
      return;
    }

    const bootstrap = async (): Promise<void> => {
      try {
        const [catalog, assignmentRows] = await Promise.all([
          listModelCatalog(token),
          listModelAssignments(token),
        ]);
        setModels(catalog);
        setAssignments(assignmentRows);
        const jobs = await listDownloadJobs(token);
        setDownloadJobs(Array.isArray(jobs) ? jobs : []);
      } catch (error) {
        setFeedback(error instanceof Error ? error.message : t("models.feedback.loadFailed"));
      }
    };

    void bootstrap();
  }, [token, t, user]);

  const assignmentByScope = useMemo(() => {
    const map = new Map<string, string[]>();
    assignments.forEach((assignment) => {
      map.set(assignment.scope, assignment.model_ids);
    });
    return map;
  }, [assignments]);

  const createModel = async (): Promise<void> => {
    if (!token || !newModelName.trim()) {
      return;
    }

    try {
      const created = await createModelCatalogItem(
        {
          name: newModelName.trim(),
          provider: newModelProvider.trim() || undefined,
          model_type: catalogModelType,
        },
        token,
      );
      setModels((currentModels) => [...currentModels, created]);
      setNewModelName("");
      setNewModelProvider("");
      setCatalogModelType("llm");
      setFeedback(t("models.feedback.created"));
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : t("models.feedback.createFailed"));
    }
  };

  const runDiscovery = async (): Promise<void> => {
    if (!token) {
      return;
    }
    try {
      const modelsFromHf = await discoverHfModels(token, {
        query: discoverQuery,
        task: discoveryModelType === "embedding" ? "feature-extraction" : "text-generation",
        model_type: discoveryModelType,
        sort: "downloads",
        limit: 12,
      });
      setDiscoveredModels(modelsFromHf);
      setSelectedModelInfo("");
      if (modelsFromHf.length === 0) {
        setFeedback(t("models.discovery.empty"));
      }
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : t("models.feedback.discoveryFailed"));
    }
  };

  const inspectModel = async (sourceId: string): Promise<void> => {
    if (!token) {
      return;
    }
    try {
      const details = await getHfModelDetails(sourceId, token);
      const filesCount = details.files.length;
      setSelectedModelInfo(`${details.source_id} • ${filesCount} files`);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : t("models.feedback.discoveryFailed"));
    }
  };

  const downloadAndRegister = async (model: HfDiscoveredModel): Promise<void> => {
    if (!token) {
      return;
    }
    try {
      const job = await startModelDownload(
        {
          source_id: model.source_id,
          name: model.name,
          model_type: discoveryModelType,
        },
        token,
      );
      setDownloadJobs((current) => [job, ...current]);
      setFeedback(t("models.feedback.downloadStarted", { source: model.source_id }));
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : t("models.feedback.downloadStartFailed"));
    }
  };

  const toggleAssignment = async (scope: string, modelId: string): Promise<void> => {
    if (!token) {
      return;
    }

    const current = assignmentByScope.get(scope) ?? [];
    const next = current.includes(modelId)
      ? current.filter((id) => id !== modelId)
      : [...current, modelId];

    try {
      const saved = await updateModelAssignment(scope, next, token);
      setAssignments((currentAssignments) => {
        const others = currentAssignments.filter((item) => item.scope !== scope);
        return [...others, saved];
      });
      setFeedback(t("models.feedback.assignmentSaved", { scope }));
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : t("models.feedback.assignmentFailed"));
    }
  };

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("models.title")}</h2>
        <p className="status-text">{t("models.subtitle")}</p>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("models.discovery.title")}</h2>
        <p className="status-text">{t("models.discovery.description")}</p>
        <div className="button-row">
          <select
            className="field-input"
            value={discoveryModelType}
            onChange={(event) => setDiscoveryModelType(event.currentTarget.value as "llm" | "embedding")}
            aria-label={t("models.discovery.typeLabel")}
          >
            <option value="llm">{t("models.types.llm")}</option>
            <option value="embedding">{t("models.types.embedding")}</option>
          </select>
          <input
            className="field-input"
            value={discoverQuery}
            onChange={(event) => setDiscoverQuery(event.currentTarget.value)}
            placeholder={t("models.discovery.queryPlaceholder")}
            aria-label={t("models.discovery.queryLabel")}
          />
          <button type="button" className="btn btn-secondary" onClick={() => void runDiscovery()}>
            {t("models.discovery.searchButton")}
          </button>
        </div>
        {selectedModelInfo && <p className="status-text">{selectedModelInfo}</p>}
        <ul className="card-stack" aria-label={t("models.discovery.listAria")}>
          {discoveredModels.map((model) => (
            <li key={model.source_id} className="status-row">
              <strong>{model.source_id}</strong>
              <span className="status-text">
                {`${t("models.discovery.downloadCount", { count: model.downloads ?? 0 })} · ${t(`models.types.${discoveryModelType}`)}`}
              </span>
              <div className="button-row">
                <button type="button" className="btn btn-ghost" onClick={() => void inspectModel(model.source_id)}>
                  {t("models.discovery.inspectButton")}
                </button>
                <button type="button" className="btn btn-primary" onClick={() => void downloadAndRegister(model)}>
                  {t("models.discovery.downloadButton")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("models.catalog.title")}</h2>
        <p className="status-text">{t("models.catalog.description")}</p>
        <div className="control-group">
          <label className="field-label" htmlFor="model-name">{t("models.catalog.nameLabel")}</label>
          <input
            id="model-name"
            className="field-input"
            value={newModelName}
            onChange={(event) => setNewModelName(event.currentTarget.value)}
          />
          <label className="field-label" htmlFor="model-provider">{t("models.catalog.providerLabel")}</label>
          <input
            id="model-provider"
            className="field-input"
            value={newModelProvider}
            onChange={(event) => setNewModelProvider(event.currentTarget.value)}
          />
          <label className="field-label" htmlFor="model-type">{t("models.catalog.typeLabel")}</label>
          <select
            id="model-type"
            className="field-input"
            value={catalogModelType}
            onChange={(event) => setCatalogModelType(event.currentTarget.value as "llm" | "embedding")}
          >
            <option value="llm">{t("models.types.llm")}</option>
            <option value="embedding">{t("models.types.embedding")}</option>
          </select>
          <button type="button" className="btn btn-primary" onClick={() => void createModel()}>
            {t("models.catalog.addButton")}
          </button>
        </div>
        <ul className="card-stack" aria-label={t("models.catalog.listAria")}>
          {models.map((model) => (
            <li key={model.id}>
              <strong>{model.name}</strong>
              <p className="status-text">{model.id} · {model.model_type ?? "unknown"} · {model.provider} · {model.status ?? "available"}</p>
            </li>
          ))}
        </ul>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("models.assignments.title")}</h2>
        <p className="status-text">{t("models.assignments.description")}</p>
        {scopeOrder.map((scope) => (
          <section key={scope} className="card-stack" aria-label={`${scope} model scope`}>
            <h3 className="section-title">{t("models.assignments.scopeTitle", { scope })}</h3>
            {models.length === 0 && <p className="status-text">{t("models.assignments.emptyCatalog")}</p>}
            {models.map((model) => {
              const checked = (assignmentByScope.get(scope) ?? []).includes(model.id);
              return (
                <label key={`${scope}-${model.id}`}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      void toggleAssignment(scope, model.id);
                    }}
                  />
                  {` ${model.name}`}
                </label>
              );
            })}
          </section>
        ))}
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("models.jobs.title")}</h2>
        <p className="status-text">{t("models.jobs.description")}</p>
        <p className="status-text">
          {hasActiveJobs ? t("models.jobs.pollingActive") : t("models.jobs.noActive")}
        </p>
        <ul className="card-stack" aria-label={t("models.jobs.listAria")}>
          {downloadJobs.map((job) => (
            <li key={job.job_id}>
              <strong>{job.source_id}</strong>
              <p className="status-text">{job.status}</p>
              {job.error_message && <p className="error-text">{job.error_message}</p>}
            </li>
          ))}
        </ul>
      </article>

      {feedback && <p className="status-text">{feedback}</p>}
    </section>
  );
}
