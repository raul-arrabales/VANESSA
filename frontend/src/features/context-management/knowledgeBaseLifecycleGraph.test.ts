import { describe, expect, it } from "vitest";
import type { KnowledgeBase } from "../../api/context";
import { expectLifecycleDefinition } from "../../test/lifecycleGraphAssertions";
import {
  createKnowledgeBaseLifecycleGraphDefinition,
  getKnowledgeBaseLifecycleState,
  KNOWLEDGE_BASE_LIFECYCLE_STATE_IDS,
  KNOWLEDGE_BASE_LIFECYCLE_TRANSITIONS,
} from "./knowledgeBaseLifecycleGraph";

const t = ((key: string) => key) as never;

function buildKnowledgeBase(overrides: Partial<KnowledgeBase> = {}): KnowledgeBase {
  return {
    id: "kb-primary",
    slug: "product-docs",
    display_name: "Product Docs",
    description: "docs",
    index_name: "kb_product_docs",
    backing_provider_key: "weaviate_local",
    lifecycle_state: "active",
    sync_status: "ready",
    schema: {},
    vectorization: {
      mode: "vanessa_embeddings",
      supports_named_vectors: true,
    },
    chunking: {
      strategy: "fixed_length",
      config: {
        unit: "tokens",
        chunk_length: 300,
        chunk_overlap: 60,
      },
    },
    document_count: 3,
    eligible_for_binding: true,
    binding_count: 0,
    ...overrides,
  };
}

describe("knowledgeBaseLifecycleGraph", () => {
  it("defines the knowledge-base lifecycle states and transitions", () => {
    const definition = createKnowledgeBaseLifecycleGraphDefinition(t);

    expectLifecycleDefinition(definition, {
      stateIds: KNOWLEDGE_BASE_LIFECYCLE_STATE_IDS,
      transitions: KNOWLEDGE_BASE_LIFECYCLE_TRANSITIONS,
      i18nBase: "contextManagement.lifecycle",
    });
  });

  it.each([
    ["archived", buildKnowledgeBase({ lifecycle_state: "archived", sync_status: "ready", document_count: 3 }), "archived"],
    ["syncing", buildKnowledgeBase({ sync_status: "syncing", document_count: 0 }), "syncing"],
    ["sync error", buildKnowledgeBase({ sync_status: "error", document_count: 3 }), "sync_error"],
    ["empty", buildKnowledgeBase({ document_count: 0 }), "empty"],
    ["ineligible", buildKnowledgeBase({ document_count: 3, eligible_for_binding: false }), "ineligible"],
    ["ready bound", buildKnowledgeBase({ document_count: 3, eligible_for_binding: true, binding_count: 1 }), "ready_bound"],
    ["ready unbound", buildKnowledgeBase({ document_count: 3, eligible_for_binding: true, binding_count: 0 }), "ready_unbound"],
  ])("classifies %s knowledge bases", (_label, knowledgeBase, expectedState) => {
    expect(getKnowledgeBaseLifecycleState(knowledgeBase)).toBe(expectedState);
  });
});
