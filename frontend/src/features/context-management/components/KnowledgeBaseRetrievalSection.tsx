import type { Dispatch, FormEvent, SetStateAction } from "react";
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
      {retrievalResults.map((result) => (
        <article key={result.id} className="panel card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h4 className="section-title">{result.title || result.id}</h4>
              <p className="status-text">
                {result.score != null && result.score_kind ? `${result.score_kind}: ${result.score}` : result.source_type ?? ""}
              </p>
            </div>
          </div>
          {result.uri ? <p className="status-text">{result.uri}</p> : null}
          <p className="status-text">{result.snippet}</p>
        </article>
      ))}
    </section>
  );
}
