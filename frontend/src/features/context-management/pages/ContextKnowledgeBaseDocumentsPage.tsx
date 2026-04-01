import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseDocumentCard } from "../components/KnowledgeBaseDocumentCard";
import { useContextKnowledgeBaseDocuments } from "../hooks/useContextKnowledgeBaseDocuments";
import { buildKnowledgeBaseDocumentViewPath } from "../routes";

export default function ContextKnowledgeBaseDocumentsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useContextKnowledgeBaseDocuments();
  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {(knowledgeBase) => (
        <section className="panel card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h3 className="section-title">{t("contextManagement.documentsBrowserTitle")}</h3>
              <p className="status-text">{t("contextManagement.documentsBrowserDescription")}</p>
            </div>
          </div>
          {detail.documents.length === 0 ? <p className="status-text">{t("contextManagement.states.noDocuments")}</p> : null}
          {detail.documents.map((document) => (
            <KnowledgeBaseDocumentCard
              key={document.id}
              document={document}
              showStatusChip
              actions={
                <Link
                  className="btn btn-secondary"
                  to={buildKnowledgeBaseDocumentViewPath(knowledgeBase.id, document.id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("contextManagement.actions.openText")}
                </Link>
              }
            />
          ))}
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
