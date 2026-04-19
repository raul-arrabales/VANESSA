import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { PlaygroundKnowledgeReference } from "../../api/playgrounds";

type Props = {
  references: PlaygroundKnowledgeReference[];
  messageId: string;
};

function isLinkableUri(value: string | null | undefined): value is string {
  if (!value) {
    return false;
  }
  return /^(https?:|file:)/i.test(value);
}

function formatPageList(pages: number[]): string {
  return [...new Set(pages)].sort((left, right) => left - right).join(", ");
}

export default function KnowledgeReferencesList({ references, messageId }: Props): JSX.Element {
  const { t } = useTranslation("common");
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
                    {isLinkableUri(reference.uri ?? fileReference) ? (
                      <a href={reference.uri ?? fileReference}>{fileReference}</a>
                    ) : (
                      <span>{fileReference}</span>
                    )}
                  </p>
                ) : null}
                {pageList ? (
                  <p className="knowledge-chat-reference-detail">
                    {t("playgrounds.references.pages", { pages: pageList })}
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
