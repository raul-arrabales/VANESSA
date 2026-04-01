import { useTranslation } from "react-i18next";
import { KnowledgeBaseDocumentCard } from "../components/KnowledgeBaseDocumentCard";
import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { isManualKnowledgeBaseDocument } from "../documentPresentation";
import { EMPTY_DOCUMENT_FORM } from "../types";
import { useContextKnowledgeBaseUpload } from "../hooks/useContextKnowledgeBaseUpload";

export default function ContextKnowledgeBaseUploadPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useContextKnowledgeBaseUpload();
  const manualDocuments = detail.documents.filter((document) => isManualKnowledgeBaseDocument(document.managed_by_source));

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {() => (
        <section className="panel card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h3 className="section-title">{t("contextManagement.uploadTitle")}</h3>
              <p className="status-text">{t("contextManagement.uploadDescription")}</p>
            </div>
          </div>

          {detail.isSuperadmin ? (
            <>
              <form className="card-stack" onSubmit={(event) => void detail.handleSubmitDocument(event)}>
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.fields.documentTitle")}</span>
                  <input
                    className="field-input"
                    value={detail.documentForm.title}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      detail.setDocumentForm((current) => ({ ...current, title: value }));
                    }}
                  />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.fields.sourceName")}</span>
                  <input
                    className="field-input"
                    value={detail.documentForm.sourceName}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      detail.setDocumentForm((current) => ({ ...current, sourceName: value }));
                    }}
                  />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.fields.uri")}</span>
                  <input
                    className="field-input"
                    value={detail.documentForm.uri}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      detail.setDocumentForm((current) => ({ ...current, uri: value }));
                    }}
                  />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.fields.documentText")}</span>
                  <textarea
                    className="field-input quote-admin-textarea"
                    value={detail.documentForm.text}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      detail.setDocumentForm((current) => ({ ...current, text: value }));
                    }}
                  />
                </label>
                <div className="form-actions">
                  <button type="submit" className="btn btn-primary">
                    {detail.documentForm.id
                      ? t("contextManagement.actions.updateDocument")
                      : t("contextManagement.actions.addDocument")}
                  </button>
                  {detail.documentForm.id ? (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => detail.setDocumentForm(EMPTY_DOCUMENT_FORM)}
                    >
                      {t("platformControl.actions.cancel")}
                    </button>
                  ) : null}
                </div>
              </form>

              <div className="card-stack">
                <label className="card-stack">
                  <span className="field-label">{t("contextManagement.fields.uploadFiles")}</span>
                  <span className="status-text">{t("contextManagement.states.supportedFileTypes")}</span>
                  <input
                    className="field-input"
                    type="file"
                    multiple
                    onChange={(event) => detail.setUploadFiles(Array.from(event.currentTarget.files ?? []))}
                  />
                </label>
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={detail.uploadFiles.length === 0}
                    onClick={() => void detail.handleUpload()}
                  >
                    {t("contextManagement.actions.upload")}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <p className="status-text">{t("contextManagement.states.readOnlyUpload")}</p>
          )}

          <div className="card-stack">
            <div className="platform-card-header">
              <div className="card-stack">
                <h4 className="section-title">{t("contextManagement.manualDocumentsTitle")}</h4>
                <p className="status-text">{t("contextManagement.manualDocumentsDescription")}</p>
              </div>
            </div>
            {manualDocuments.length === 0 ? <p className="status-text">{t("contextManagement.states.noManualDocuments")}</p> : null}
            {manualDocuments.map((document) => (
              <KnowledgeBaseDocumentCard
                key={document.id}
                document={document}
                titleAs="h5"
                excerptLength={180}
                actions={detail.isSuperadmin ? (
                  <>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() =>
                        detail.setDocumentForm({
                          id: document.id,
                          title: document.title,
                          sourceName: document.source_name ?? "",
                          uri: document.uri ?? "",
                          text: document.text,
                        })
                      }
                    >
                      {t("contextManagement.actions.edit")}
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() => void detail.handleDeleteDocument(document.id)}
                    >
                      {t("contextManagement.actions.deleteDocument")}
                    </button>
                  </>
                ) : null}
              />
            ))}
          </div>
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
