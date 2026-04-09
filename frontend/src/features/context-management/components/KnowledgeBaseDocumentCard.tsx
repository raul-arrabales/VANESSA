import type { ReactNode } from "react";
import type { KnowledgeDocument } from "../../../api/context";
import { buildKnowledgeBaseDocumentExcerpt } from "../documentPresentation";
import { KnowledgeBaseDocumentMetadata } from "./KnowledgeBaseDocumentMetadata";

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
  return (
    <article className="panel panel-nested card-stack">
      <KnowledgeBaseDocumentMetadata document={document} titleAs={titleAs} showStatusChip={showStatusChip} />
      <p className="status-text">{buildKnowledgeBaseDocumentExcerpt(document.text, excerptLength)}</p>
      {actions ? <div className="form-actions">{actions}</div> : null}
    </article>
  );
}
