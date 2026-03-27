import { useAuth } from "../../../auth/AuthProvider";
import QuoteManagementEditorModal from "../../../components/QuoteManagementEditorModal";
import QuoteManagementFilters from "../../../components/QuoteManagementFilters";
import QuoteManagementSummary from "../../../components/QuoteManagementSummary";
import QuoteManagementTable from "../../../components/QuoteManagementTable";
import { useQuoteManagement } from "../hooks/useQuoteManagement";
import { useTranslation } from "react-i18next";

export default function QuoteManagementPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const {
    summary,
    items,
    selectedQuote,
    draft,
    filterDraft,
    page,
    total,
    totalPages,
    isLoadingSummary,
    isLoadingList,
    isLoadingDetail,
    isSaving,
    isCreating,
    isEditorOpen,
    error,
    success,
    setDraft,
    setFilterDraft,
    setPage,
    submitSearch,
    beginCreate,
    closeEditor,
    selectQuote,
    saveQuote,
  } = useQuoteManagement(token);

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

        <QuoteManagementSummary isLoading={isLoadingSummary} summary={summary} />
      </article>

      <QuoteManagementFilters
        filterDraft={filterDraft}
        setFilterDraft={setFilterDraft}
        onSubmit={submitSearch}
      />

      <QuoteManagementTable
        items={items}
        total={total}
        page={page}
        totalPages={totalPages}
        isLoading={isLoadingList}
        onSelectQuote={(quoteId) => void selectQuote(quoteId)}
        onPreviousPage={() => setPage((current) => Math.max(1, current - 1))}
        onNextPage={() => setPage((current) => Math.min(totalPages, current + 1))}
      />

      <QuoteManagementEditorModal
        isOpen={isEditorOpen}
        isCreating={isCreating}
        isLoadingDetail={isLoadingDetail}
        isSaving={isSaving}
        selectedQuote={selectedQuote}
        draft={draft}
        setDraft={setDraft}
        onClose={closeEditor}
        onSave={() => void saveQuote()}
      />
    </section>
  );
}
