import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../auth/authApi";
import { useAuth } from "../auth/AuthProvider";
import {
  createQuote,
  fetchQuoteById,
  fetchQuotes,
  fetchQuoteSummary,
  updateQuote,
  type QuoteAdminItem,
  type QuoteListFilters,
  type QuotePayload,
  type QuoteSummary,
} from "../api/quoteAdmin";

type QuoteFormState = {
  language: string;
  text: string;
  author: string;
  source_universe: string;
  tone: string;
  tags: string;
  is_active: boolean;
  is_approved: boolean;
  origin: string;
  external_ref: string;
};

const PAGE_SIZE = 10;

function blankForm(): QuoteFormState {
  return {
    language: "en",
    text: "",
    author: "",
    source_universe: "Original",
    tone: "reflective",
    tags: "",
    is_active: true,
    is_approved: true,
    origin: "local",
    external_ref: "",
  };
}

function formFromQuote(quote: QuoteAdminItem): QuoteFormState {
  return {
    language: quote.language,
    text: quote.text,
    author: quote.author,
    source_universe: quote.source_universe,
    tone: quote.tone,
    tags: quote.tags.join(", "),
    is_active: quote.is_active,
    is_approved: quote.is_approved,
    origin: quote.origin,
    external_ref: quote.external_ref ?? "",
  };
}

function formToPayload(form: QuoteFormState): QuotePayload {
  return {
    language: form.language,
    text: form.text,
    author: form.author,
    source_universe: form.source_universe,
    tone: form.tone,
    tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    is_active: form.is_active,
    is_approved: form.is_approved,
    origin: form.origin,
    external_ref: form.external_ref,
  };
}

export default function QuoteManagementPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [summary, setSummary] = useState<QuoteSummary | null>(null);
  const [items, setItems] = useState<QuoteAdminItem[]>([]);
  const [selectedQuote, setSelectedQuote] = useState<QuoteAdminItem | null>(null);
  const [draft, setDraft] = useState<QuoteFormState>(blankForm);
  const [filters, setFilters] = useState<QuoteListFilters>({});
  const [filterDraft, setFilterDraft] = useState<QuoteListFilters>({});
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoadingSummary, setIsLoadingSummary] = useState(true);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadSummary = useCallback(async (): Promise<void> => {
    setIsLoadingSummary(true);
    try {
      setSummary(await fetchQuoteSummary(token));
    } catch (loadError) {
      if (loadError instanceof ApiError) {
        setError(loadError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setIsLoadingSummary(false);
    }
  }, [t, token]);

  const loadQuotes = useCallback(async (nextPage: number, nextFilters: QuoteListFilters): Promise<void> => {
    setIsLoadingList(true);
    try {
      const result = await fetchQuotes(token, nextPage, PAGE_SIZE, nextFilters);
      setItems(result.items);
      setPage(result.page);
      setTotal(result.total);
    } catch (loadError) {
      if (loadError instanceof ApiError) {
        setError(loadError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setIsLoadingList(false);
    }
  }, [t, token]);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    void loadQuotes(page, filters);
  }, [filters, loadQuotes, page]);

  const selectQuote = async (quoteId: number): Promise<void> => {
    setError("");
    setSuccess("");
    setIsCreating(false);
    setIsEditorOpen(true);
    setIsLoadingDetail(true);
    try {
      const quote = await fetchQuoteById(quoteId, token);
      setSelectedQuote(quote);
      setDraft(formFromQuote(quote));
    } catch (loadError) {
      if (loadError instanceof ApiError) {
        setError(loadError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const submitSearch = async (): Promise<void> => {
    setError("");
    setSuccess("");
    setPage(1);
    setFilters({ ...filterDraft });
  };

  const beginCreate = (): void => {
    setIsCreating(true);
    setIsEditorOpen(true);
    setSelectedQuote(null);
    setDraft(blankForm());
    setError("");
    setSuccess("");
  };

  const closeEditor = (): void => {
    setIsEditorOpen(false);
    setIsCreating(false);
    setSelectedQuote(null);
    setIsLoadingDetail(false);
    setDraft(blankForm());
  };

  const saveQuote = async (): Promise<void> => {
    setError("");
    setSuccess("");
    setIsSaving(true);

    try {
      if (isCreating) {
        await createQuote(formToPayload(draft), token);
        setSuccess(t("quoteAdmin.feedback.created"));
        setIsCreating(false);
        await loadSummary();
        await loadQuotes(1, filters);
        setPage(1);
        closeEditor();
      } else if (selectedQuote) {
        await updateQuote(selectedQuote.id, formToPayload(draft), token);
        setSuccess(t("quoteAdmin.feedback.updated"));
        await loadSummary();
        await loadQuotes(page, filters);
        closeEditor();
      }
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setError(submitError.message);
      } else {
        setError(t("auth.error.unknown"));
      }
    } finally {
      setIsSaving(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="card-stack quote-admin-page">
      <article className="panel card-stack">
        <div className="quote-admin-header">
          <div>
            <h2 className="section-title">{t("quoteAdmin.title")}</h2>
            <p className="status-text">{t("quoteAdmin.description")}</p>
          </div>
          <button className="btn btn-primary" type="button" onClick={beginCreate}>
            {t("quoteAdmin.actions.new")}
          </button>
        </div>

        {error && <p className="status-text error-text">{error}</p>}
        {success && <p className="status-text success-text">{success}</p>}

        {isLoadingSummary || !summary ? (
          <p className="status-text">{t("quoteAdmin.summary.loading")}</p>
        ) : (
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
        )}
      </article>

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
          <button className="btn btn-secondary" type="button" onClick={() => void submitSearch()}>
            {t("quoteAdmin.actions.search")}
          </button>
        </div>
      </article>

      <article className="panel card-stack">
        <div className="quote-admin-table-header">
          <h3 className="section-title">{t("quoteAdmin.list.title")}</h3>
          <p className="status-text">{t("quoteAdmin.list.results", { total })}</p>
        </div>

        {isLoadingList ? (
          <p className="status-text">{t("quoteAdmin.list.loading")}</p>
        ) : items.length === 0 ? (
          <p className="status-text">{t("quoteAdmin.list.empty")}</p>
        ) : (
          <div className="health-table-wrap">
            <table className="health-table" aria-label={t("quoteAdmin.list.tableAria")}>
              <thead>
                <tr>
                  <th>{t("quoteAdmin.list.columns.id")}</th>
                  <th>{t("quoteAdmin.list.columns.text")}</th>
                  <th>{t("quoteAdmin.list.columns.author")}</th>
                  <th>{t("quoteAdmin.list.columns.source")}</th>
                  <th>{t("quoteAdmin.list.columns.tone")}</th>
                  <th>{t("quoteAdmin.list.columns.language")}</th>
                  <th>{t("quoteAdmin.list.columns.updated")}</th>
                  <th>{t("quoteAdmin.list.columns.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{item.text}</td>
                    <td>{item.author}</td>
                    <td>{item.source_universe}</td>
                    <td>{item.tone}</td>
                    <td>{item.language}</td>
                    <td>{item.updated_at ?? "--"}</td>
                    <td>
                      <button className="btn btn-ghost" type="button" onClick={() => void selectQuote(item.id)}>
                        {t("quoteAdmin.actions.edit")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="form-actions">
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          >
            {t("quoteAdmin.pagination.previous")}
          </button>
          <p className="status-text">{t("quoteAdmin.pagination.page", { page, totalPages })}</p>
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page >= totalPages}
          >
            {t("quoteAdmin.pagination.next")}
          </button>
        </div>
      </article>

      {isEditorOpen && (
        <div className="modal-backdrop" role="presentation">
          <div
            className="modal-card panel quote-admin-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="quote-admin-editor-title"
          >
            <div className="quote-admin-table-header">
              <h3 id="quote-admin-editor-title" className="section-title">
                {isCreating ? t("quoteAdmin.editor.createTitle") : t("quoteAdmin.editor.editTitle")}
              </h3>
              {!isCreating && selectedQuote && <p className="status-text">#{selectedQuote.id}</p>}
            </div>

            {isLoadingDetail ? (
              <p className="status-text">{t("quoteAdmin.editor.loading")}</p>
            ) : (
              <>
                <div className="quote-admin-filter-grid">
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.language")}</span>
                    <input className="field-input" value={draft.language} onChange={(event) => setDraft((current) => ({ ...current, language: event.target.value }))} />
                  </label>
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.author")}</span>
                    <input className="field-input" value={draft.author} onChange={(event) => setDraft((current) => ({ ...current, author: event.target.value }))} />
                  </label>
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.sourceUniverse")}</span>
                    <input className="field-input" value={draft.source_universe} onChange={(event) => setDraft((current) => ({ ...current, source_universe: event.target.value }))} />
                  </label>
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.tone")}</span>
                    <input className="field-input" value={draft.tone} onChange={(event) => setDraft((current) => ({ ...current, tone: event.target.value }))} />
                  </label>
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.origin")}</span>
                    <input className="field-input" value={draft.origin} onChange={(event) => setDraft((current) => ({ ...current, origin: event.target.value }))} />
                  </label>
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.externalRef")}</span>
                    <input className="field-input" value={draft.external_ref} onChange={(event) => setDraft((current) => ({ ...current, external_ref: event.target.value }))} />
                  </label>
                </div>

                <label className="control-group">
                  <span className="field-label">{t("quoteAdmin.editor.fields.text")}</span>
                  <textarea
                    className="field-input quote-admin-textarea"
                    value={draft.text}
                    onChange={(event) => setDraft((current) => ({ ...current, text: event.target.value }))}
                  />
                </label>

                <label className="control-group">
                  <span className="field-label">{t("quoteAdmin.editor.fields.tags")}</span>
                  <input className="field-input" value={draft.tags} onChange={(event) => setDraft((current) => ({ ...current, tags: event.target.value }))} />
                </label>

                <div className="quote-admin-checkbox-row">
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.isActive")}</span>
                    <input type="checkbox" checked={draft.is_active} onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))} />
                  </label>
                  <label className="control-group">
                    <span className="field-label">{t("quoteAdmin.editor.fields.isApproved")}</span>
                    <input type="checkbox" checked={draft.is_approved} onChange={(event) => setDraft((current) => ({ ...current, is_approved: event.target.checked }))} />
                  </label>
                </div>

                <div className="modal-actions">
                  <button className="btn btn-secondary" type="button" onClick={closeEditor} disabled={isSaving}>
                    {t("quoteAdmin.actions.cancel")}
                  </button>
                  <button className="btn btn-primary" type="button" onClick={() => void saveQuote()} disabled={isSaving}>
                    {isSaving ? t("quoteAdmin.actions.saving") : t("quoteAdmin.actions.save")}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
