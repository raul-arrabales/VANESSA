import { useTranslation } from "react-i18next";
import type { KnowledgeBaseQueryResult } from "../../../api/context";
import type { RetrievalDisplayItem } from "../../ai-shared/retrieval";

type Props = {
  item: RetrievalDisplayItem<KnowledgeBaseQueryResult>;
  isExpanded: boolean;
  onToggle: () => void;
};

export function KnowledgeBaseRetrievalResultCard({
  item,
  isExpanded,
  onToggle,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const result = item.raw;
  const scoreLabelKey = item.displayScoreKind === "hybrid_score"
    ? "contextManagement.fields.hybridScore"
    : item.displayScoreKind === "keyword_score"
      ? "contextManagement.fields.keywordScore"
      : "contextManagement.fields.similarity";

  return (
    <article className="panel card-stack context-retrieval-result-card">
      <button
        type="button"
        className="context-retrieval-result-toggle"
        aria-expanded={isExpanded}
        aria-controls={`retrieval-result-details-${result.id}`}
        aria-label={t(
          isExpanded ? "contextManagement.actions.collapseChunkResult" : "contextManagement.actions.expandChunkResult",
          { title: item.displayTitle },
        )}
        onClick={onToggle}
      >
        <div className="context-retrieval-result-summary">
            <div className="platform-card-header context-retrieval-result-header">
              <div className="card-stack">
                <h4 className="section-title">{item.displayTitle}</h4>
                <p className="status-text">
                  {t(scoreLabelKey)}: {(item.displayScoreValue ?? 0).toFixed(3)}
                </p>
              </div>
            <span
              className="context-retrieval-result-expand-indicator"
              data-expanded={isExpanded ? "true" : "false"}
              aria-hidden="true"
            >
              <svg viewBox="0 0 16 16" focusable="false">
                <path d="M4 6l4 4 4-4" />
              </svg>
            </span>
          </div>
          <p className="status-text context-retrieval-result-preview">{item.displaySnippet}</p>
        </div>
        <span className="sr-only">
          {t(
            isExpanded ? "contextManagement.actions.collapseChunkResult" : "contextManagement.actions.expandChunkResult",
            { title: item.displayTitle },
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
          {item.displayComponentScoreRows.length > 0 ? (
            <div className="card-stack">
              {item.displayComponentScoreRows.map((row) => (
                <p key={row.kind} className="status-text">
                  {t(row.kind === "semantic_score"
                    ? "contextManagement.fields.semanticScore"
                    : "contextManagement.fields.keywordScore")}: {row.value.toFixed(3)}
                </p>
              ))}
            </div>
          ) : null}
          {item.displayMetadataEntries.length > 0 ? (
            <div className="card-stack">
              <p className="field-label">{t("contextManagement.fields.chunkMetadata")}</p>
              {item.displayMetadataEntries.map(({ key, value }) => (
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
}
