import { useMemo, useState, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import type { PlaygroundKnowledgeReference } from "../../api/playgrounds";
import { buildUrl } from "../../auth/authApi";
import { readStoredToken } from "../../auth/storage";
import { useActionFeedback } from "../../feedback/ActionFeedbackProvider";

type Props = {
  references: PlaygroundKnowledgeReference[];
  messageId: string;
};

function isLinkableUri(value: string | null | undefined): value is string {
  if (!value) {
    return false;
  }
  return /^https?:/i.test(value);
}

function formatPageList(pages: number[]): string {
  return [...new Set(pages)].sort((left, right) => left - right).join(", ");
}

function isPdfReference(reference: PlaygroundKnowledgeReference): boolean {
  const value = reference.file_reference ?? reference.uri ?? "";
  return /\.pdf(?:$|[?#])/i.test(value);
}

function firstPageFragment(reference: PlaygroundKnowledgeReference): string {
  if (!isPdfReference(reference)) {
    return "";
  }
  const pages = reference.pages;
  const firstPage = [...new Set(pages ?? [])].filter((page) => Number.isInteger(page) && page > 0).sort((left, right) => left - right)[0];
  return firstPage ? `#page=${firstPage}` : "";
}

function appendPageFragment(href: string, reference: PlaygroundKnowledgeReference): string {
  const fragment = firstPageFragment(reference);
  return fragment ? `${href.split("#", 1)[0]}${fragment}` : href;
}

export default function KnowledgeReferencesList({ references, messageId }: Props): JSX.Element {
  const { t } = useTranslation("common");
  const { showErrorFeedback } = useActionFeedback();
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

  const handleSourceFileClick = async (
    event: MouseEvent<HTMLAnchorElement>,
    reference: PlaygroundKnowledgeReference,
  ): Promise<void> => {
    if (!reference.file_url) {
      return;
    }
    event.preventDefault();
    const token = readStoredToken();
    if (!token) {
      showErrorFeedback(t("playgrounds.references.openSourceAuthRequired"));
      return;
    }
    const targetWindow = window.open("about:blank", "_blank");
    if (!targetWindow) {
      showErrorFeedback(t("playgrounds.references.openSourcePopupBlocked"));
      return;
    }
    targetWindow.opener = null;
    try {
      const response = await fetch(buildUrl(reference.file_url), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(t("playgrounds.references.openSourceFailed"));
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      targetWindow.location.href = `${objectUrl}${firstPageFragment(reference)}`;
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch (error) {
      targetWindow.close();
      showErrorFeedback(error, t("playgrounds.references.openSourceFailed"));
    }
  };

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
            const sourceHref = reference.file_url
              ? appendPageFragment(buildUrl(reference.file_url), reference)
              : isLinkableUri(reference.uri)
                ? appendPageFragment(reference.uri, reference)
                : null;
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
                      onClick={(event) => handleSourceFileClick(event, reference)}
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
