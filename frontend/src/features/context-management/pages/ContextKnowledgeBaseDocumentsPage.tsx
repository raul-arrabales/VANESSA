import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeDocument } from "../../../api/context";
import ActionIcon from "../../../components/ActionIcon";
import { CompactRegistryList } from "../../../components/CompactRegistryList";
import IconButton from "../../../components/IconButton";
import IconLink from "../../../components/IconLink";
import ModalDialog from "../../../components/ModalDialog";
import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseDocumentCard } from "../components/KnowledgeBaseDocumentCard";
import { useContextKnowledgeBaseDocuments } from "../hooks/useContextKnowledgeBaseDocuments";
import { formatMetadataValue } from "../metadataEditor";
import { buildKnowledgeBaseDocumentViewPath } from "../routes";

export default function ContextKnowledgeBaseDocumentsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useContextKnowledgeBaseDocuments();
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
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
          <CompactRegistryList>
            {detail.documents.map((document) => (
              <KnowledgeBaseDocumentCard
                key={document.id}
                document={document}
                showStatusChip
                actions={
                  <>
                    <IconButton label={t("contextManagement.actionLabels.viewMetadata", { title: document.title })} onClick={() => setSelectedDocument(document)}>
                      <ActionIcon name="metadata" />
                    </IconButton>
                    <IconLink
                      to={buildKnowledgeBaseDocumentViewPath(knowledgeBase.id, document.id)}
                      target="_blank"
                      rel="noreferrer"
                      label={t("contextManagement.actionLabels.openText", { title: document.title })}
                    >
                      <ActionIcon name="open" />
                    </IconLink>
                  </>
                }
              />
            ))}
          </CompactRegistryList>
          {selectedDocument ? (
            <ModalDialog
              title={t("contextManagement.metadataViewer.title", { title: selectedDocument.title })}
              description={t("contextManagement.metadataViewer.description")}
              onClose={() => setSelectedDocument(null)}
              initialFocusRef={closeButtonRef}
              actions={(
                <button
                  ref={closeButtonRef}
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setSelectedDocument(null)}
                >
                  {t("actionFeedback.dialog.close")}
                </button>
              )}
            >
              {Object.entries(selectedDocument.metadata).length === 0 ? (
                <p className="status-text">{t("contextManagement.metadataViewer.empty")}</p>
              ) : (
                <dl className="card-stack" aria-label={t("contextManagement.metadataViewer.aria")}>
                  {Object.entries(selectedDocument.metadata).map(([key, value]) => (
                    <div key={key} className="context-metadata-viewer-row">
                      <dt className="field-label">{key}</dt>
                      <dd className="status-text">{formatMetadataValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </ModalDialog>
          ) : null}
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
