import { useTranslation } from "react-i18next";
import type { HfDiscoveredModel, ModelDownloadJob } from "../../../api/modelops/types";

type LocalDiscoveryPanelProps = {
  taskKey: string;
  query: string;
  discoveredModels: HfDiscoveredModel[];
  selectedModelInfo: string;
  downloadJobs: ModelDownloadJob[];
  hasActiveJobs: boolean;
  onTaskKeyChange: (value: string) => void;
  onQueryChange: (value: string) => void;
  onSearch: () => Promise<void>;
  onInspect: (sourceId: string) => Promise<void>;
  onDownload: (model: HfDiscoveredModel) => Promise<void>;
};

export default function LocalDiscoveryPanel({
  taskKey,
  query,
  discoveredModels,
  selectedModelInfo,
  downloadJobs,
  hasActiveJobs,
  onTaskKeyChange,
  onQueryChange,
  onSearch,
  onInspect,
  onDownload,
}: LocalDiscoveryPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.local.discoveryTitle")}</h2>
      <div className="button-row">
        <select className="field-input" value={taskKey} onChange={(event) => onTaskKeyChange(event.currentTarget.value)} aria-label={t("modelOps.fields.task")}>
          <option value="llm">LLM</option>
          <option value="embeddings">Embeddings</option>
        </select>
        <input
          className="field-input"
          placeholder={t("modelOps.local.discoveryPlaceholder")}
          value={query}
          onChange={(event) => onQueryChange(event.currentTarget.value)}
        />
        <button type="button" className="btn btn-secondary" onClick={() => void onSearch()}>
          {t("modelOps.actions.searchHf")}
        </button>
      </div>
      {selectedModelInfo && <p className="status-text">{selectedModelInfo}</p>}
      <ul className="card-stack" aria-label={t("modelOps.local.discoveryResultsAria")}>
        {discoveredModels.map((model) => (
          <li key={model.source_id} className="status-row">
            <span>{`${model.source_id} · ${model.downloads ?? 0} downloads`}</span>
            <div className="button-row">
              <button type="button" className="btn btn-ghost" onClick={() => void onInspect(model.source_id)}>
                {t("modelOps.actions.inspect")}
              </button>
              <button type="button" className="btn btn-primary" onClick={() => void onDownload(model)}>
                {t("modelOps.actions.download")}
              </button>
            </div>
          </li>
        ))}
      </ul>
      <p className="status-text">
        {hasActiveJobs ? t("modelOps.local.pollingActive") : t("modelOps.local.noActiveJobs")}
      </p>
      <ul className="card-stack" aria-label={t("modelOps.local.downloadJobsAria")}>
        {downloadJobs.map((job) => (
          <li key={job.job_id} className="status-row">
            <span>{`${job.source_id} · ${job.status}`}</span>
            {job.error_message && <span className="error-text">{job.error_message}</span>}
          </li>
        ))}
      </ul>
    </article>
  );
}
