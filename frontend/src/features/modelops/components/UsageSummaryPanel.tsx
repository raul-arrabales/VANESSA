import { useTranslation } from "react-i18next";
import type { ModelUsageSummary } from "../../../api/modelops/types";

type UsageSummaryPanelProps = {
  usage: ModelUsageSummary | null;
};

export default function UsageSummaryPanel({ usage }: UsageSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const metrics = Object.entries(usage?.metrics ?? {});

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.detail.usageTitle")}</h2>
      <p className="status-text">{`${t("modelOps.detail.totalRequests")}: ${usage?.total_requests ?? 0}`}</p>
      {metrics.length === 0 ? (
        <p className="status-text">{t("modelOps.detail.noUsageMetrics")}</p>
      ) : (
        <ul className="card-stack" aria-label="Usage metrics">
          {metrics.map(([metricKey, metric]) => (
            <li key={metricKey} className="status-row">
              <span>{`${metricKey}: ${metric.value} (${metric.requests} requests)`}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
