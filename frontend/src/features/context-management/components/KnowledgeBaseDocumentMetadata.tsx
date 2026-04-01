import { createElement } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeDocument } from "../../../api/context";

type HeadingTag = "h3" | "h4" | "h5";

type KnowledgeBaseDocumentMetadataProps = {
  document: KnowledgeDocument;
  titleAs?: HeadingTag | null;
  showStatusChip?: boolean;
};

export function KnowledgeBaseDocumentMetadata({
  document,
  titleAs = "h4",
  showStatusChip = false,
}: KnowledgeBaseDocumentMetadataProps): JSX.Element {
  const { t } = useTranslation("common");
  const sourceLabel = document.managed_by_source
    ? t("contextManagement.states.documentManagedBySource", {
        source: document.source_name || document.source_type,
        path: document.source_path || "unknown",
      })
    : document.source_name || t("contextManagement.states.manualDocument");
  const title = titleAs
    ? createElement(titleAs, { className: "section-title" }, document.title)
    : null;

  return (
    <>
      <div className="platform-card-header">
        <div className="card-stack">
          {title}
          <p className="status-text">{sourceLabel}</p>
        </div>
        {showStatusChip ? (
          <span className="status-chip status-chip-neutral">
            {document.managed_by_source
              ? t("contextManagement.states.sourceManaged")
              : t("contextManagement.states.manualDocument")}
          </span>
        ) : null}
      </div>
      {document.uri ? <p className="status-text">{document.uri}</p> : null}
      {document.source_path ? (
        <p className="status-text">
          {t("contextManagement.fields.sourcePath")}: {document.source_path}
        </p>
      ) : null}
      <p className="status-text">
        {t("contextManagement.fields.chunkCount")}: {document.chunk_count}
      </p>
    </>
  );
}
