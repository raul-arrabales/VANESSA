import { useTranslation } from "react-i18next";
import type { Dispatch, SetStateAction } from "react";
import type { QuoteAdminItem } from "../api/quoteAdmin";
import type { QuoteFormState } from "../hooks/useQuoteManagement";

type QuoteManagementEditorModalProps = {
  isOpen: boolean;
  isCreating: boolean;
  isLoadingDetail: boolean;
  isSaving: boolean;
  selectedQuote: QuoteAdminItem | null;
  draft: QuoteFormState;
  setDraft: Dispatch<SetStateAction<QuoteFormState>>;
  onClose: () => void;
  onSave: () => void;
};

export default function QuoteManagementEditorModal({
  isOpen,
  isCreating,
  isLoadingDetail,
  isSaving,
  selectedQuote,
  draft,
  setDraft,
  onClose,
  onSave,
}: QuoteManagementEditorModalProps): JSX.Element | null {
  const { t } = useTranslation("common");

  if (!isOpen) {
    return null;
  }

  return (
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
                className="field-input form-textarea"
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
              <button className="btn btn-secondary" type="button" onClick={onClose} disabled={isSaving}>
                {t("quoteAdmin.actions.cancel")}
              </button>
              <button className="btn btn-primary" type="button" onClick={() => void onSave()} disabled={isSaving}>
                {isSaving ? t("quoteAdmin.actions.saving") : t("quoteAdmin.actions.save")}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
