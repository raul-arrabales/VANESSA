import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBaseQueryResult } from "../../../api/context";
import { formatElapsedDuration } from "../../../utils/timing";
import {
  mapKnowledgeBaseQueryResultToDisplayItem,
  sortRetrievalResultsByRelevance,
} from "../../ai-shared/retrieval";
import { KnowledgeBaseRetrievalResultCard } from "./KnowledgeBaseRetrievalResultCard";

type Props = {
  retrievalResults: KnowledgeBaseQueryResult[];
  retrievalResultCount: number | null;
  retrievalDurationMs: number | null;
  completedQueryId: number;
};

export function KnowledgeBaseRetrievalResults({
  retrievalResults,
  retrievalResultCount,
  retrievalDurationMs,
  completedQueryId,
}: Props): JSX.Element {
  const { t, i18n } = useTranslation("common");
  const [expandedResultId, setExpandedResultId] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setExpandedResultId(null);
  }, [retrievalResults]);

  useEffect(() => {
    if (completedQueryId < 1) {
      return;
    }
    resultsRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [completedQueryId]);

  const displayItems = useMemo(
    () => sortRetrievalResultsByRelevance(retrievalResults)
      .map((result, index) => mapKnowledgeBaseQueryResultToDisplayItem(result, index)),
    [retrievalResults],
  );

  return (
    <div ref={resultsRef} className="card-stack">
      {retrievalResultCount !== null ? (
        <p className="status-text">{t("contextManagement.states.queryResultCount", { count: retrievalResultCount })}</p>
      ) : null}
      {retrievalDurationMs !== null ? (
        <p className="status-text">
          {t("contextManagement.states.queryDuration", {
            duration: formatElapsedDuration(retrievalDurationMs, i18n.language),
          })}
        </p>
      ) : null}
      {retrievalResults.length === 0 && retrievalResultCount !== null ? (
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
