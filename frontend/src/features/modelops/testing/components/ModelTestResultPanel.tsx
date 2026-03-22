import { useTranslation } from "react-i18next";
import type { ModelTestResult, ModelTestRun } from "../../../../api/modelops/types";

type ModelTestResultPanelProps = {
  result: ModelTestResult | null;
  latestTest: ModelTestRun | null;
  summary: string;
  error: string;
};

export default function ModelTestResultPanel({
  result,
  latestTest,
  summary,
  error,
}: ModelTestResultPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.testing.resultTitle")}</h2>
      {summary && <p className="status-text">{summary}</p>}
      {result ? (
        <>
          <p className="status-text">
            {result.success ? t("modelOps.testing.success") : t("modelOps.testing.failure")}
          </p>
          {typeof result.latency_ms === "number" && (
            <p className="status-text">{t("modelOps.testing.latency", { value: Math.round(result.latency_ms) })}</p>
          )}
          {typeof result.response_text === "string" && result.response_text && (
            <div className="card-stack">
              <strong>{t("modelOps.testing.responseTitle")}</strong>
              <pre className="status-text">{result.response_text}</pre>
            </div>
          )}
          {typeof result.dimension === "number" && (
            <p className="status-text">{t("modelOps.testing.dimension", { value: result.dimension })}</p>
          )}
        </>
      ) : latestTest ? (
        <>
          {!summary && <p className="status-text">{latestTest.summary}</p>}
          {typeof latestTest.latency_ms === "number" && (
            <p className="status-text">{t("modelOps.testing.latency", { value: Math.round(latestTest.latency_ms) })}</p>
          )}
        </>
      ) : (
        <p className="status-text">{t("modelOps.testing.noResult")}</p>
      )}
      {error && <p className="error-text">{error}</p>}
    </article>
  );
}
