import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { KnowledgeBaseDocumentsSection } from "../components/KnowledgeBaseDocumentsSection";
import { KnowledgeBaseOverviewSection } from "../components/KnowledgeBaseOverviewSection";
import { KnowledgeBaseRetrievalSection } from "../components/KnowledgeBaseRetrievalSection";
import { KnowledgeBaseSourcesSection } from "../components/KnowledgeBaseSourcesSection";
import { KnowledgeBaseSyncHistorySection } from "../components/KnowledgeBaseSyncHistorySection";
import { useContextKnowledgeBaseDetail } from "../hooks/useContextKnowledgeBaseDetail";

export default function ContextKnowledgeBaseDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useContextKnowledgeBaseDetail();
  const knowledgeBase = detail.knowledgeBase;

  return (
    <section className="card-stack">
      <div className="platform-card-header panel">
        <div className="card-stack">
          <h2 className="section-title">{knowledgeBase?.display_name ?? t("contextManagement.detailTitle")}</h2>
          <p className="status-text">{knowledgeBase?.description || t("contextManagement.detailDescription")}</p>
        </div>
        <Link className="btn btn-secondary" to="/control/context">
          {t("contextManagement.actions.back")}
        </Link>
      </div>

      {detail.loading ? <section className="panel"><p className="status-text">{t("contextManagement.states.loading")}</p></section> : null}

      {knowledgeBase ? (
        <>
          <KnowledgeBaseOverviewSection
            knowledgeBase={knowledgeBase}
            form={detail.form}
            isSuperadmin={detail.isSuperadmin}
            isResyncing={detail.isResyncing}
            onFormChange={detail.setForm}
            onSave={detail.handleSaveKnowledgeBase}
            onDelete={detail.handleDeleteKnowledgeBase}
            onResync={detail.handleResyncKnowledgeBase}
          />
          <KnowledgeBaseSourcesSection
            sources={detail.sources}
            sourceForm={detail.sourceForm}
            sourceDirectoryBrowser={detail.sourceDirectoryBrowser}
            isSuperadmin={detail.isSuperadmin}
            syncingSourceId={detail.syncingSourceId}
            onSourceFormChange={detail.setSourceForm}
            onOpenDirectoryBrowser={detail.handleOpenSourceDirectoryBrowser}
            onCloseDirectoryBrowser={detail.handleCloseSourceDirectoryBrowser}
            onBrowseDirectories={detail.handleBrowseSourceDirectories}
            onUseCurrentDirectory={detail.handleUseCurrentSourceDirectory}
            onSubmit={detail.handleSubmitSource}
            onDelete={detail.handleDeleteSource}
            onSync={detail.handleSyncSource}
          />
          <KnowledgeBaseSyncHistorySection syncRuns={detail.syncRuns} />
          <KnowledgeBaseRetrievalSection
            retrievalQuery={detail.retrievalQuery}
            retrievalTopK={detail.retrievalTopK}
            retrievalResults={detail.retrievalResults}
            retrievalResultCount={detail.retrievalResultCount}
            isQuerying={detail.isQuerying}
            onQueryChange={detail.setRetrievalQuery}
            onTopKChange={detail.setRetrievalTopK}
            onSubmit={detail.handleTestRetrieval}
          />
          <KnowledgeBaseDocumentsSection
            knowledgeBase={knowledgeBase}
            documents={detail.documents}
            documentForm={detail.documentForm}
            uploadFiles={detail.uploadFiles}
            isSuperadmin={detail.isSuperadmin}
            onDocumentFormChange={detail.setDocumentForm}
            onUploadFilesChange={detail.setUploadFiles}
            onSubmitDocument={detail.handleSubmitDocument}
            onDeleteDocument={detail.handleDeleteDocument}
            onUpload={detail.handleUpload}
          />
        </>
      ) : null}
    </section>
  );
}
