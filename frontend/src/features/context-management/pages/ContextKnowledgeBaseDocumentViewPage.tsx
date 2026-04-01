import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { KnowledgeBaseDocumentMetadata } from "../components/KnowledgeBaseDocumentMetadata";
import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { useContextKnowledgeBaseDocuments } from "../hooks/useContextKnowledgeBaseDocuments";
import { buildKnowledgeBaseWorkspacePath } from "../routes";

export default function ContextKnowledgeBaseDocumentViewPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { documentId = "" } = useParams();
  const detail = useContextKnowledgeBaseDocuments();
  const document = detail.documents.find((entry) => entry.id === documentId) ?? null;

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {(knowledgeBase) => (
        <section className="panel card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h3 className="section-title">{document?.title ?? t("contextManagement.documentViewTitle")}</h3>
              <p className="status-text">{t("contextManagement.documentViewDescription")}</p>
            </div>
            <div className="form-actions">
              <Link
                className="btn btn-secondary"
                to={buildKnowledgeBaseWorkspacePath(knowledgeBase.id, "documents")}
              >
                {t("contextManagement.actions.backToDocuments")}
              </Link>
            </div>
          </div>

          {!document ? <p className="status-text">{t("contextManagement.states.documentNotFound")}</p> : null}

          {document ? (
            <>
              <KnowledgeBaseDocumentMetadata document={document} titleAs={null} showStatusChip />
              <pre className="status-text" style={{ whiteSpace: "pre-wrap" }}>{document.text}</pre>
            </>
          ) : null}
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
