import { describe, expect, it } from "vitest";
import type { PlaygroundKnowledgeReference } from "../../api/playgrounds";
import {
  formatPageList,
  getKnowledgeReferenceSourceHref,
} from "./knowledgeReferenceLinks";

function reference(overrides: Partial<PlaygroundKnowledgeReference>): PlaygroundKnowledgeReference {
  return {
    id: "ref-1",
    citation_label: "[1]",
    title: "Architecture",
    pages: [],
    source_ids: [],
    ...overrides,
  };
}

describe("knowledgeReferenceLinks", () => {
  it("formats unique sorted page lists", () => {
    expect(formatPageList([3, 2, 3, 1])).toBe("1, 2, 3");
  });

  it("adds the first PDF page fragment to backend source-file links", () => {
    expect(
      getKnowledgeReferenceSourceHref(reference({
        file_reference: "docs/manual.pdf",
        file_url: "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
        pages: [4, 2],
      })),
    ).toBe("/api/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file#page=2");
  });

  it("does not add page fragments to non-PDF source-file links", () => {
    expect(
      getKnowledgeReferenceSourceHref(reference({
        file_reference: "docs/manual.md",
        file_url: "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
        pages: [2],
      })),
    ).toBe("/api/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file");
  });

  it("falls back to HTTP URIs and ignores unopenable local URI values", () => {
    expect(
      getKnowledgeReferenceSourceHref(reference({
        uri: "https://example.test/manual.pdf?download=1",
        pages: [7],
      })),
    ).toBe("https://example.test/manual.pdf?download=1#page=7");

    expect(
      getKnowledgeReferenceSourceHref(reference({
        uri: "file:///tmp/manual.pdf",
        pages: [7],
      })),
    ).toBeNull();
  });
});
