import type { TFunction } from "i18next";
import type { KnowledgeBase } from "../../api/context";
import { buildLifecycleGraphDefinition, type LifecycleGraphDefinition, type LifecycleTransitionDefinition } from "../../components/LifecycleGraph";

export const KNOWLEDGE_BASE_LIFECYCLE_STATE_IDS = [
  "empty",
  "syncing",
  "sync_error",
  "ineligible",
  "ready_unbound",
  "ready_bound",
  "archived",
] as const;

export type KnowledgeBaseLifecycleState = typeof KNOWLEDGE_BASE_LIFECYCLE_STATE_IDS[number];

export const KNOWLEDGE_BASE_LIFECYCLE_TRANSITIONS: LifecycleTransitionDefinition[] = [
  { from: "empty", to: "syncing" },
  { from: "syncing", to: "sync_error" },
  { from: "syncing", to: "ready_unbound" },
  { from: "syncing", to: "ready_bound" },
  { from: "sync_error", to: "syncing" },
  { from: "ineligible", to: "syncing" },
  { from: "ready_unbound", to: "syncing" },
  { from: "ready_bound", to: "syncing" },
  { from: "ready_unbound", to: "ready_bound" },
  { from: "ready_bound", to: "ready_unbound" },
  { from: "empty", to: "archived" },
  { from: "syncing", to: "archived" },
  { from: "sync_error", to: "archived" },
  { from: "ineligible", to: "archived" },
  { from: "ready_unbound", to: "archived" },
  { from: "ready_bound", to: "archived" },
  { from: "archived", to: "empty" },
];

export function createKnowledgeBaseLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return buildLifecycleGraphDefinition(t, {
    artifactType: "knowledge-base",
    stateIds: KNOWLEDGE_BASE_LIFECYCLE_STATE_IDS,
    i18nBase: "contextManagement.lifecycle",
    positions: [
      { x: 90, y: 82 },
      { x: 240, y: 82 },
      { x: 390, y: 82 },
      { x: 540, y: 82 },
      { x: 150, y: 214 },
      { x: 370, y: 214 },
      { x: 620, y: 214 },
    ],
    transitions: KNOWLEDGE_BASE_LIFECYCLE_TRANSITIONS,
  });
}

export function getKnowledgeBaseLifecycleState(knowledgeBase: KnowledgeBase): KnowledgeBaseLifecycleState {
  if (knowledgeBase.lifecycle_state === "archived") {
    return "archived";
  }
  if (knowledgeBase.sync_status === "syncing") {
    return "syncing";
  }
  if (knowledgeBase.sync_status === "error") {
    return "sync_error";
  }
  if (knowledgeBase.document_count === 0) {
    return "empty";
  }
  if (!knowledgeBase.eligible_for_binding) {
    return "ineligible";
  }
  if ((knowledgeBase.binding_count ?? 0) > 0) {
    return "ready_bound";
  }
  return "ready_unbound";
}

export function getKnowledgeBaseLifecycleSummary(t: TFunction<"common">, knowledgeBase: KnowledgeBase): string {
  const noneLabel = t("platformControl.summary.none");
  const backingProvider =
    knowledgeBase.backing_provider?.display_name ??
    knowledgeBase.backing_provider?.provider_key ??
    knowledgeBase.backing_provider_key ??
    noneLabel;
  const embeddingProvider =
    knowledgeBase.vectorization.embedding_provider?.display_name ??
    knowledgeBase.vectorization.embedding_provider?.provider_key ??
    knowledgeBase.vectorization.embedding_provider_instance_id ??
    noneLabel;
  const embeddingResource =
    knowledgeBase.vectorization.embedding_resource?.display_name ??
    knowledgeBase.vectorization.embedding_resource?.provider_resource_id ??
    knowledgeBase.vectorization.embedding_resource_id ??
    noneLabel;
  const eligibility = knowledgeBase.eligible_for_binding
    ? t("contextManagement.states.eligible")
    : t("contextManagement.states.ineligible");
  const syncError = knowledgeBase.last_sync_error
    ? t("contextManagement.lifecycle.syncErrorSuffix", { error: knowledgeBase.last_sync_error })
    : "";

  return t("contextManagement.lifecycle.summary", {
    lifecycleState: knowledgeBase.lifecycle_state,
    syncStatus: knowledgeBase.sync_status,
    documentCount: knowledgeBase.document_count,
    bindingCount: knowledgeBase.binding_count ?? 0,
    eligibility,
    backingProvider,
    embeddingProvider,
    embeddingResource,
    syncError,
  });
}
