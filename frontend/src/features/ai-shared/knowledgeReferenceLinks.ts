import type { PlaygroundKnowledgeReference } from "../../api/playgrounds";
import { buildUrl } from "../../auth/authApi";

export function formatPageList(pages: number[]): string {
  return [...new Set(pages)].sort((left, right) => left - right).join(", ");
}

export function firstPageFragment(reference: PlaygroundKnowledgeReference): string {
  if (!isPdfReference(reference)) {
    return "";
  }
  const firstPage = [...new Set(reference.pages ?? [])]
    .filter((page) => Number.isInteger(page) && page > 0)
    .sort((left, right) => left - right)[0];
  return firstPage ? `#page=${firstPage}` : "";
}

export function appendPageFragment(href: string, reference: PlaygroundKnowledgeReference): string {
  const fragment = firstPageFragment(reference);
  return fragment ? `${href.split("#", 1)[0]}${fragment}` : href;
}

export function getKnowledgeReferenceSourceHref(reference: PlaygroundKnowledgeReference): string | null {
  if (reference.file_url) {
    return appendPageFragment(buildUrl(reference.file_url), reference);
  }
  if (isLinkableUri(reference.uri)) {
    return appendPageFragment(reference.uri, reference);
  }
  return null;
}

function isLinkableUri(value: string | null | undefined): value is string {
  if (!value) {
    return false;
  }
  return /^https?:/i.test(value);
}

function isPdfReference(reference: PlaygroundKnowledgeReference): boolean {
  const value = reference.file_reference ?? reference.uri ?? "";
  return /\.pdf(?:$|[?#])/i.test(value);
}
