import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { PlaygroundKnowledgeReference } from "../../api/playgrounds";
import { formatPageList, getKnowledgeReferenceSourceHref } from "./knowledgeReferenceLinks";
import { useKnowledgeSourceFileOpener } from "./useKnowledgeSourceFileOpener";

type Props = {
  references: PlaygroundKnowledgeReference[];
  messageId: string;
};

export default function KnowledgeReferencesList({ references, messageId }: Props): JSX.Element {
  const { t } = useTranslation("common");
  const openSourceFile = useKnowledgeSourceFileOpener();
  const [expanded, setExpanded] = useState(false);
  const detailsId = `knowledge-message-references-${messageId}`;
  const referenceCount = references.length;
  const sortedReferences = useMemo(
    () => references,
    [references],
  );

  if (referenceCount === 0) {
    return <></>;
  }

  return (
    <section className="knowledge-chat-references">
      <button
        type="button"
        className="knowledge-chat-references-toggle"
        aria-expanded={expanded}
        aria-controls={detailsId}
        onClick={() => setExpanded((current) => !current)}
      >
        {t("playgrounds.references.toggle", { count: referenceCount })}
      </button>
      {expanded ? (
        <div id={detailsId} className="knowledge-chat-reference-list">
          {sortedReferences.map((reference) => {
            const fileReference = reference.file_reference ?? reference.uri ?? "";
            const pageList = formatPageList(reference.pages ?? []);
            const sourceHref = getKnowledgeReferenceSourceHref(reference);
            return (
              <article key={reference.id} className="knowledge-chat-reference">
                <div className="knowledge-chat-reference-heading">
                  <span className="knowledge-chat-reference-label">{reference.citation_label}</span>
                  <strong className="knowledge-chat-reference-title">{reference.title}</strong>
                </div>
                {reference.description ? (
                  <p className="knowledge-chat-reference-description">{reference.description}</p>
                ) : null}
                {fileReference ? (
                  <p className="knowledge-chat-reference-detail">
                    <span>{t("playgrounds.references.file")}: </span>
                    <span>{fileReference}</span>
                  </p>
                ) : null}
                {pageList ? (
                  <p className="knowledge-chat-reference-detail">
                    {t("playgrounds.references.pages", { pages: pageList })}
                  </p>
                ) : null}
                {sourceHref ? (
                  <p className="knowledge-chat-reference-detail">
                    <a
                      href={sourceHref}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(event) => openSourceFile(event, reference)}
                    >
                      {t("playgrounds.references.openSource")}
                    </a>
                  </p>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
