import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeDocument } from "../../../api/context";
import { buildKnowledgeBaseDocumentExcerpt } from "../documentPresentation";

type KnowledgeBaseDocumentCardProps = {
  document: KnowledgeDocument;
  titleAs?: "h4" | "h5";
  excerptLength?: number;
  showStatusChip?: boolean;
  actions?: ReactNode;
};

export function KnowledgeBaseDocumentCard({
  document,
  titleAs = "h4",
  excerptLength = 240,
  showStatusChip = false,
  actions = null,
}: KnowledgeBaseDocumentCardProps): JSX.Element {
  const { t } = useTranslation("common");
  const sourceLabel = document.managed_by_source
    ? t("contextManagement.states.documentManagedBySource", {
        source: document.source_name || document.source_type,
        path: document.source_path || "unknown",
      })
    : document.source_name || t("contextManagement.states.manualDocument");
  const TitleTag = titleAs;

  return (
    <article className="context-compact-list-item" role="listitem">
      <div className="context-compact-list-main">
        <div className="context-compact-list-heading">
          <TitleTag className="section-title">{document.title}</TitleTag>
          {showStatusChip ? (
            <span className="status-chip status-chip-neutral">
              {document.managed_by_source
                ? t("contextManagement.states.sourceManaged")
                : t("contextManagement.states.manualDocument")}
            </span>
          ) : null}
        </div>
        <p className="status-text context-compact-description">{buildKnowledgeBaseDocumentExcerpt(document.text, excerptLength)}</p>
        <div className="context-compact-meta-row">
          <code className="code-inline">{document.id}</code>
          <span>{sourceLabel}</span>
          {document.uri ? <span>{document.uri}</span> : null}
          {document.source_path ? <span>{t("contextManagement.fields.sourcePath")}: {document.source_path}</span> : null}
          <span>{t("contextManagement.fields.chunkCount")}: {document.chunk_count}</span>
        </div>
      </div>
      {actions ? <div className="context-compact-actions">{actions}</div> : null}
    </article>
  );
}
