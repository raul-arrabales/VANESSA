export function buildKnowledgeBaseDocumentExcerpt(text: string, maxLength = 240): string {
  const normalized = text.trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

export function isManualKnowledgeBaseDocument(managedBySource: boolean | null | undefined): boolean {
  return !managedBySource;
}
