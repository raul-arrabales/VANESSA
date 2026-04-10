import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { KnowledgeBaseMetadataEditor } from "../components/KnowledgeBaseMetadataEditor";
import { KnowledgeBaseDocumentCard } from "../components/KnowledgeBaseDocumentCard";
import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { isManualKnowledgeBaseDocument } from "../documentPresentation";
import { metadataEntriesFromRecord } from "../metadataEditor";
import { EMPTY_DOCUMENT_FORM } from "../types";
import { useContextKnowledgeBaseUpload } from "../hooks/useContextKnowledgeBaseUpload";

type UploadPageView = "manual" | "upload" | "manage";

const UPLOAD_PAGE_VIEW_ORDER: ReadonlyArray<UploadPageView> = ["manual", "upload", "manage"];

function resolveUploadPageView(value: string | null, isSuperadmin: boolean): UploadPageView {
  const defaultView: UploadPageView = isSuperadmin ? "manual" : "manage";
  if ((value === "manual" || value === "upload") && isSuperadmin) {
    return value;
  }
  if (value === "manage") {
    return value;
  }
  return defaultView;
}

export default function ContextKnowledgeBaseUploadPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useContextKnowledgeBaseUpload();
  const [searchParams, setSearchParams] = useSearchParams();
  const manualDocuments = detail.documents.filter((document) => isManualKnowledgeBaseDocument(document.managed_by_source));
  const activeView = resolveUploadPageView(searchParams.get("view"), detail.isSuperadmin);
  const availableViews = UPLOAD_PAGE_VIEW_ORDER.filter((view) => detail.isSuperadmin || view === "manage");
  const submenuItems = availableViews.map((view) => ({
    id: view,
    label: t(`contextManagement.uploadViews.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));

  function handleChangeView(view: UploadPageView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  function handleEditDocument(document: (typeof manualDocuments)[number]): void {
    detail.setDocumentForm({
      id: document.id,
      title: document.title,
      sourceName: document.source_name ?? "",
      uri: document.uri ?? "",
      text: document.text,
      metadataEntries: metadataEntriesFromRecord(document.metadata, detail.knowledgeBase?.schema ?? {}),
    });
    handleChangeView("manual");
  }

  return (
    <ContextKnowledgeBaseWorkspaceFrame
      knowledgeBase={detail.knowledgeBase}
      loading={detail.loading}
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("contextManagement.uploadViews.aria")} />}
    >
      {() => (
        <section className="card-stack">
          {activeView === "manual" ? (
            <section className="panel card-stack">
              <div className="platform-card-header">
                <div className="card-stack">
                  <h4 className="section-title">{t("contextManagement.uploadViews.manualTitle")}</h4>
                  <p className="status-text">{t("contextManagement.uploadViews.manualDescription")}</p>
                </div>
              </div>
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
                <KnowledgeBaseMetadataEditor
                  schemaProperties={detail.knowledgeBase?.schema.properties ?? []}
                  entries={detail.documentForm.metadataEntries}
                  onChange={(metadataEntries) => {
                    detail.setDocumentForm((current) => ({ ...current, metadataEntries }));
                  }}
                />
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
            </section>
          ) : null}

          {activeView === "upload" ? (
            <section className="panel card-stack">
              <div className="platform-card-header">
                <div className="card-stack">
                  <h4 className="section-title">{t("contextManagement.uploadViews.uploadTitle")}</h4>
                  <p className="status-text">{t("contextManagement.uploadViews.uploadDescription")}</p>
                </div>
              </div>
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
                <KnowledgeBaseMetadataEditor
                  schemaProperties={detail.knowledgeBase?.schema.properties ?? []}
                  entries={detail.uploadMetadataEntries}
                  onChange={detail.setUploadMetadataEntries}
                />
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
            </section>
          ) : null}

          {activeView === "manage" ? (
            <section className="panel card-stack">
              <div className="platform-card-header">
                <div className="card-stack">
                  <h4 className="section-title">{t("contextManagement.uploadViews.manageTitle")}</h4>
                  <p className="status-text">{t("contextManagement.uploadViews.manageDescription")}</p>
                </div>
              </div>
              {!detail.isSuperadmin ? <p className="status-text">{t("contextManagement.states.readOnlyUpload")}</p> : null}
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
                        onClick={() => handleEditDocument(document)}
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
            </section>
          ) : null}
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
