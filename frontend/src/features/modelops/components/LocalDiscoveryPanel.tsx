import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { HfDiscoveredModel } from "../../../api/modelops/types";

type LocalDiscoveryPanelProps = {
  taskKey: string;
  query: string;
  feedback: string;
  discoveredModels: HfDiscoveredModel[];
  completedSearchId: number;
  completedLoadMoreId: number;
  latestLoadedBatchStartIndex: number | null;
  canLoadMoreModels: boolean;
  isLoadingMoreModels: boolean;
  onTaskKeyChange: (value: string) => void;
  onQueryChange: (value: string) => void;
  onSearch: () => Promise<void>;
  onLoadMore: () => Promise<void>;
  onInspect: (sourceId: string) => Promise<void>;
  onDownload: (model: HfDiscoveredModel) => Promise<void>;
};

export default function LocalDiscoveryPanel({
  taskKey,
  query,
  feedback,
  discoveredModels,
  completedSearchId,
  completedLoadMoreId,
  latestLoadedBatchStartIndex,
  canLoadMoreModels,
  isLoadingMoreModels,
  onTaskKeyChange,
  onQueryChange,
  onSearch,
  onLoadMore,
  onInspect,
  onDownload,
}: LocalDiscoveryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const resultsRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (completedSearchId < 1) {
      return;
    }
    resultsRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [completedSearchId]);

  useEffect(() => {
    if (
      completedLoadMoreId < 1 ||
      latestLoadedBatchStartIndex === null ||
      discoveredModels.length <= latestLoadedBatchStartIndex
    ) {
      return;
    }
    resultsRef.current
      ?.querySelector<HTMLElement>(`[data-discovery-result-index="${latestLoadedBatchStartIndex}"]`)
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
  }, [completedLoadMoreId, latestLoadedBatchStartIndex, discoveredModels.length]);

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
      {feedback ? <p className="status-text">{feedback}</p> : null}
      <ul ref={resultsRef} className="card-stack" aria-label={t("modelOps.local.discoveryResultsAria")}>
        {discoveredModels.map((model, index) => (
          <li
            key={model.source_id}
            className="modelops-discovery-row"
            data-discovery-result-index={index}
          >
            <div className="button-row modelops-discovery-actions">
              <button type="button" className="btn btn-ghost" onClick={() => void onInspect(model.source_id)}>
                {t("modelOps.actions.inspect")}
              </button>
              <button type="button" className="btn btn-primary" onClick={() => void onDownload(model)}>
                {t("modelOps.actions.download")}
              </button>
            </div>
            <div className="card-stack">
              <strong>
                <span className="modelops-discovery-result-number">{index + 1}.</span> {model.source_id}
              </strong>
              <span className="status-text">
                {[
                  t("modelOps.local.downloadCount", { count: model.downloads ?? 0 }),
                  t("modelOps.local.likeCount", { count: model.likes ?? 0 }),
                ].join(" · ")}
              </span>
            </div>
          </li>
        ))}
      </ul>
      {canLoadMoreModels ? (
        <div className="button-row">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isLoadingMoreModels}
            onClick={() => void onLoadMore()}
          >
            {isLoadingMoreModels ? t("modelOps.local.loadingMore") : t("modelOps.local.loadMore")}
          </button>
        </div>
      ) : null}
    </article>
  );
}
