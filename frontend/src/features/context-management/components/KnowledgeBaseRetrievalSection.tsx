import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBaseQueryResult } from "../../../api/context";

type Props = {
  retrievalQuery: string;
  retrievalTopK: string;
  retrievalResults: KnowledgeBaseQueryResult[];
  retrievalResultCount: number | null;
  isQuerying: boolean;
  onQueryChange: Dispatch<SetStateAction<string>>;
  onTopKChange: Dispatch<SetStateAction<string>>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function KnowledgeBaseRetrievalSection({
  retrievalQuery,
  retrievalTopK,
  retrievalResults,
  retrievalResultCount,
  isQuerying,
  onQueryChange,
  onTopKChange,
  onSubmit,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const [expandedResultId, setExpandedResultId] = useState<string | null>(null);

  useEffect(() => {
    setExpandedResultId(null);
  }, [retrievalResults]);

  const formatMetadataValue = (value: unknown): string => {
    if (typeof value === "string") {
      return value;
    }
    if (typeof value === "number" || typeof value === "boolean" || typeof value === "bigint") {
      return String(value);
    }
    if (value instanceof Date) {
      return value.toISOString();
    }
    return JSON.stringify(value);
  };

  const getVisibleMetadataEntries = (metadata: Record<string, unknown>): Array<[string, string]> => (
    Object.entries(metadata)
      .filter(([, value]) => value !== null && value !== undefined && !(typeof value === "string" && value.trim() === ""))
      .map(([key, value]) => [key, formatMetadataValue(value)])
      .filter(([, value]) => value !== undefined && value !== "undefined")
  );

  const sortedResults = useMemo(
    () => [...retrievalResults].sort((left, right) => right.similarity - left.similarity),
    [retrievalResults],
  );

  const buildPreview = (text: string): string => {
    const tokens = text.trim().split(/\s+/).filter(Boolean);
    if (tokens.length <= 24) {
      return tokens.join(" ");
    }
    return `${tokens.slice(0, 24).join(" ")}…`;
  };

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h3 className="section-title">{t("contextManagement.queryTitle")}</h3>
          <p className="status-text">{t("contextManagement.queryDescription")}</p>
        </div>
      </div>
      <form className="card-stack" onSubmit={(event) => void onSubmit(event)}>
        <label className="card-stack">
          <span className="field-label">{t("contextManagement.fields.queryText")}</span>
          <textarea
            className="field-input quote-admin-textarea"
            value={retrievalQuery}
            onChange={(event) => onQueryChange(event.currentTarget.value)}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("contextManagement.fields.topK")}</span>
          <input
            className="field-input"
            type="number"
            min={1}
            step={1}
            value={retrievalTopK}
            onChange={(event) => onTopKChange(event.currentTarget.value)}
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={isQuerying || !retrievalQuery.trim()}>
            {isQuerying ? t("contextManagement.actions.querying") : t("contextManagement.actions.testRetrieval")}
          </button>
        </div>
      </form>
      {retrievalResultCount !== null ? (
        <p className="status-text">{t("contextManagement.states.queryResultCount", { count: retrievalResultCount })}</p>
      ) : null}
      {retrievalResults.length === 0 && retrievalResultCount !== null ? (
        <p className="status-text">{t("contextManagement.states.noQueryResults")}</p>
      ) : null}
      {sortedResults.map((result) => {
        const metadataEntries = getVisibleMetadataEntries(result.metadata);
        const isExpanded = expandedResultId === result.id;
        const preview = buildPreview(result.text);
        const title = result.title || result.id;

        return (
          <article key={result.id} className="panel card-stack context-retrieval-result-card">
            <button
              type="button"
              className="context-retrieval-result-toggle"
              aria-expanded={isExpanded}
              aria-controls={`retrieval-result-details-${result.id}`}
              aria-label={t(
                isExpanded ? "contextManagement.actions.collapseChunkResult" : "contextManagement.actions.expandChunkResult",
                { title },
              )}
              onClick={() => setExpandedResultId((current) => (current === result.id ? null : result.id))}
            >
              <div className="context-retrieval-result-summary">
                <div className="platform-card-header">
                  <div className="card-stack">
                    <h4 className="section-title">{title}</h4>
                    <p className="status-text">
                      {t("contextManagement.fields.similarity")}: {result.similarity.toFixed(3)}
                    </p>
                  </div>
                </div>
                <p className="status-text context-retrieval-result-preview">{preview}</p>
              </div>
              <span className="sr-only">
                {t(
                  isExpanded ? "contextManagement.actions.collapseChunkResult" : "contextManagement.actions.expandChunkResult",
                  { title },
                )}
              </span>
            </button>
            {isExpanded ? (
              <div id={`retrieval-result-details-${result.id}`} className="card-stack context-retrieval-result-details">
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.fields.chunkText")}</span>
                  <textarea
                    className="field-input quote-admin-textarea context-retrieval-result-text"
                    value={result.text}
                    readOnly
                    aria-label={t("contextManagement.fields.chunkText")}
                  />
                </label>
                <p className="status-text">
                  {t("contextManagement.fields.chunkLength")}: {t("contextManagement.states.chunkLengthTokens", { count: result.chunk_length_tokens })}
                </p>
                {metadataEntries.length > 0 ? (
                  <div className="card-stack">
                    <p className="field-label">{t("contextManagement.fields.chunkMetadata")}</p>
                    {metadataEntries.map(([key, value]) => (
                      <p key={key} className="status-text">
                        {key}: {value}
                      </p>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
