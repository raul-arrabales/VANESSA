import { useTranslation } from "react-i18next";
import type { QuoteSummary } from "../api/quoteAdmin";

type QuoteManagementSummaryProps = {
  isLoading: boolean;
  summary: QuoteSummary | null;
};

export default function QuoteManagementSummary({
  isLoading,
  summary,
}: QuoteManagementSummaryProps): JSX.Element {
  const { t } = useTranslation("common");

  if (isLoading || !summary) {
    return <p className="status-text">{t("quoteAdmin.summary.loading")}</p>;
  }

  return (
    <div className="quote-admin-summary-grid">
      <article className="quote-admin-summary-card">
        <p className="field-label">{t("quoteAdmin.summary.total")}</p>
        <p className="quote-admin-summary-value">{summary.total}</p>
      </article>
      <article className="quote-admin-summary-card">
        <p className="field-label">{t("quoteAdmin.summary.active")}</p>
        <p className="quote-admin-summary-value">{summary.active}</p>
      </article>
      <article className="quote-admin-summary-card">
        <p className="field-label">{t("quoteAdmin.summary.approved")}</p>
        <p className="quote-admin-summary-value">{summary.approved}</p>
      </article>
      <article className="quote-admin-summary-card">
        <p className="field-label">{t("quoteAdmin.summary.languages")}</p>
        <p className="status-text">{summary.by_language.map((item) => `${item.value}: ${item.count}`).join(" / ") || "--"}</p>
      </article>
      <article className="quote-admin-summary-card">
        <p className="field-label">{t("quoteAdmin.summary.tones")}</p>
        <p className="status-text">{summary.by_tone.map((item) => `${item.value}: ${item.count}`).join(" / ") || "--"}</p>
      </article>
      <article className="quote-admin-summary-card">
        <p className="field-label">{t("quoteAdmin.summary.origins")}</p>
        <p className="status-text">{summary.by_origin.map((item) => `${item.value}: ${item.count}`).join(" / ") || "--"}</p>
      </article>
    </div>
  );
}
