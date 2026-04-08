import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBaseQueryResult } from "../../../api/context";
import {
  mapKnowledgeBaseQueryResultToDisplayItem,
  sortRetrievalResultsByRelevance,
} from "../../ai-shared/retrieval";
import { KnowledgeBaseRetrievalResultCard } from "./KnowledgeBaseRetrievalResultCard";

type Props = {
  retrievalResults: KnowledgeBaseQueryResult[];
  retrievalResultCount: number | null;
};

export function KnowledgeBaseRetrievalResults({
  retrievalResults,
  retrievalResultCount,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const [expandedResultId, setExpandedResultId] = useState<string | null>(null);

  useEffect(() => {
    setExpandedResultId(null);
  }, [retrievalResults]);

  const displayItems = useMemo(
    () => sortRetrievalResultsByRelevance(retrievalResults)
      .map((result, index) => mapKnowledgeBaseQueryResultToDisplayItem(result, index)),
    [retrievalResults],
  );

  return (
    <>
      {retrievalResultCount !== null ? (
        <p className="status-text">{t("contextManagement.states.queryResultCount", { count: retrievalResultCount })}</p>
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
    </>
  );
}
