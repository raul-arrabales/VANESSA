import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBase, KnowledgeDocument } from "../../../api/context";
import { EMPTY_DOCUMENT_FORM, type DocumentFormState } from "../types";

type Props = {
  knowledgeBase: KnowledgeBase;
  documents: KnowledgeDocument[];
  documentForm: DocumentFormState;
  uploadFiles: File[];
  isSuperadmin: boolean;
  onDocumentFormChange: Dispatch<SetStateAction<DocumentFormState>>;
  onUploadFilesChange: Dispatch<SetStateAction<File[]>>;
  onSubmitDocument: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onDeleteDocument: (documentId: string) => Promise<void>;
  onUpload: () => Promise<void>;
};

export function KnowledgeBaseDocumentsSection({
  knowledgeBase,
  documents,
  documentForm,
  uploadFiles,
  isSuperadmin,
  onDocumentFormChange,
  onUploadFilesChange,
  onSubmitDocument,
  onDeleteDocument,
  onUpload,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <h3 className="section-title">{t("contextManagement.documentsTitle")}</h3>
      {knowledgeBase.deployment_usage?.length ? (
        <div className="card-stack">
          <p className="status-text">{t("contextManagement.usageTitle")}</p>
          {knowledgeBase.deployment_usage.map((usage) => (
            <p key={`${usage.deployment_profile.id}-${usage.capability}`} className="status-text">
              <strong>{usage.deployment_profile.display_name}</strong> ({usage.deployment_profile.slug}) - {usage.capability}
            </p>
          ))}
        </div>
      ) : null}

      {isSuperadmin ? (
        <>
          <form className="card-stack" onSubmit={(event) => void onSubmitDocument(event)}>
            <label className="card-stack">
              <span className="field-label">{t("contextManagement.fields.documentTitle")}</span>
              <input
                className="field-input"
                value={documentForm.title}
                onChange={(event) => onDocumentFormChange((current) => ({ ...current, title: event.currentTarget.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("contextManagement.fields.sourceName")}</span>
              <input
                className="field-input"
                value={documentForm.sourceName}
                onChange={(event) => onDocumentFormChange((current) => ({ ...current, sourceName: event.currentTarget.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("contextManagement.fields.uri")}</span>
              <input
                className="field-input"
                value={documentForm.uri}
                onChange={(event) => onDocumentFormChange((current) => ({ ...current, uri: event.currentTarget.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("contextManagement.fields.documentText")}</span>
              <textarea
                className="field-input quote-admin-textarea"
                value={documentForm.text}
                onChange={(event) => onDocumentFormChange((current) => ({ ...current, text: event.currentTarget.value }))}
              />
            </label>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary">
                {documentForm.id ? t("contextManagement.actions.updateDocument") : t("contextManagement.actions.addDocument")}
              </button>
              {documentForm.id ? (
                <button type="button" className="btn btn-secondary" onClick={() => onDocumentFormChange(EMPTY_DOCUMENT_FORM)}>
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
                onChange={(event) => onUploadFilesChange(Array.from(event.currentTarget.files ?? []))}
              />
            </label>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={uploadFiles.length === 0}
                onClick={() => void onUpload()}
              >
                {t("contextManagement.actions.upload")}
              </button>
            </div>
          </div>
        </>
      ) : null}

      {documents.length === 0 ? <p className="status-text">{t("contextManagement.states.noDocuments")}</p> : null}
      {documents.map((document) => (
        <article key={document.id} className="panel card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h4 className="section-title">{document.title}</h4>
              <p className="status-text">
                {document.managed_by_source
                  ? t("contextManagement.states.documentManagedBySource", {
                      source: document.source_name || document.source_type,
                      path: document.source_path || "unknown",
                    })
                  : document.source_name || document.source_type}
              </p>
            </div>
            {isSuperadmin && !document.managed_by_source ? (
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() =>
                    onDocumentFormChange({
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
                <button type="button" className="btn btn-danger" onClick={() => void onDeleteDocument(document.id)}>
                  {t("contextManagement.actions.deleteDocument")}
                </button>
              </div>
            ) : null}
          </div>
          {document.managed_by_source ? (
            <p className="status-text">{t("contextManagement.states.documentManagedReadOnly")}</p>
          ) : null}
          {document.uri ? <p className="status-text">{document.uri}</p> : null}
          <pre className="status-text" style={{ whiteSpace: "pre-wrap" }}>{document.text}</pre>
        </article>
      ))}
    </section>
  );
}
