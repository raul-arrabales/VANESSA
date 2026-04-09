import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatElapsedDuration } from "../../../utils/timing";
import {
  mapKnowledgeBaseQueryResultToDisplayItem,
  sortRetrievalResultsByRelevance,
} from "../../ai-shared/retrieval";
import type { KnowledgeBaseRetrievalRunState } from "../hooks/useContextKnowledgeBaseRetrieval";
import { KnowledgeBaseRetrievalResultCard } from "./KnowledgeBaseRetrievalResultCard";

type Props = {
  retrievalRun: KnowledgeBaseRetrievalRunState | null;
};

export function KnowledgeBaseRetrievalResults({ retrievalRun }: Props): JSX.Element {
  const { t, i18n } = useTranslation("common");
  const [expandedResultId, setExpandedResultId] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setExpandedResultId(null);
  }, [retrievalRun?.results]);

  useEffect(() => {
    if ((retrievalRun?.completedQueryId ?? 0) < 1) {
      return;
    }
    resultsRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [retrievalRun?.completedQueryId]);

  const displayItems = useMemo(
    () => sortRetrievalResultsByRelevance(retrievalRun?.results ?? [])
      .map((result, index) => mapKnowledgeBaseQueryResultToDisplayItem(result, index)),
    [retrievalRun?.results],
  );

  return (
    <div ref={resultsRef} className="card-stack">
      {retrievalRun !== null ? (
        <p className="status-text">{t("contextManagement.states.queryResultCount", { count: retrievalRun.resultCount })}</p>
      ) : null}
      {retrievalRun !== null ? (
        <p className="status-text">
          {t("contextManagement.states.queryDuration", {
            duration: formatElapsedDuration(retrievalRun.durationMs, i18n.language),
          })}
        </p>
      ) : null}
      {retrievalRun !== null && retrievalRun.results.length === 0 ? (
        <p className="status-text">{t("contextManagement.states.noQueryResults")}</p>
      ) : null}
      {displayItems.map((item) => (
        <KnowledgeBaseRetrievalResultCard
          key={item.id}
          item={item}
          isExpanded={expandedResultId === item.id}
          onToggle={() => setExpandedResultId((current) => (current === item.id ? null : item.id))}
        />
      ))}
    </div>
  );
}
