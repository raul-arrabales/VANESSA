import { useTranslation } from "react-i18next";
import type { Dispatch, SetStateAction } from "react";
import type { QuoteListFilters } from "../api/quoteAdmin";

type QuoteManagementFiltersProps = {
  filterDraft: QuoteListFilters;
  setFilterDraft: Dispatch<SetStateAction<QuoteListFilters>>;
  onSubmit: () => void;
};

export default function QuoteManagementFilters({
  filterDraft,
  setFilterDraft,
  onSubmit,
}: QuoteManagementFiltersProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h3 className="section-title">{t("quoteAdmin.filters.title")}</h3>
      <div className="quote-admin-filter-grid">
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.query")}</span>
          <input
            className="field-input"
            value={filterDraft.query ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, query: event.target.value }))}
          />
        </label>
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.language")}</span>
          <input
            className="field-input"
            value={filterDraft.language ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, language: event.target.value }))}
          />
        </label>
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.source")}</span>
          <input
            className="field-input"
            value={filterDraft.source_universe ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, source_universe: event.target.value }))}
          />
        </label>
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.tone")}</span>
          <input
            className="field-input"
            value={filterDraft.tone ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, tone: event.target.value }))}
          />
        </label>
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.origin")}</span>
          <input
            className="field-input"
            value={filterDraft.origin ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, origin: event.target.value }))}
          />
        </label>
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.createdFrom")}</span>
          <input
            className="field-input"
            type="date"
            value={filterDraft.created_from ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, created_from: event.target.value }))}
          />
        </label>
        <label className="control-group">
          <span className="field-label">{t("quoteAdmin.filters.createdTo")}</span>
          <input
            className="field-input"
            type="date"
            value={filterDraft.created_to ?? ""}
            onChange={(event) => setFilterDraft((current) => ({ ...current, created_to: event.target.value }))}
          />
        </label>
      </div>
      <div className="form-actions">
        <button className="btn btn-secondary" type="button" onClick={onSubmit}>
          {t("quoteAdmin.actions.search")}
        </button>
      </div>
    </article>
  );
}
