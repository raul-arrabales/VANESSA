import type { TFunction } from "i18next";
import type { KnowledgeBase } from "../../api/context";
import { buildLifecycleGraphDefinition, type LifecycleGraphDefinition, type LifecycleSummaryRow, type LifecycleTransitionDefinition } from "../../components/lifecycle-graph";

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

export function getKnowledgeBaseLifecycleSummaryRows(t: TFunction<"common">, knowledgeBase: KnowledgeBase): LifecycleSummaryRow[] {
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

  const rows: LifecycleSummaryRow[] = [
    { label: t("contextManagement.lifecycle.summaryLabels.lifecycleState"), value: knowledgeBase.lifecycle_state },
    { label: t("contextManagement.lifecycle.summaryLabels.syncStatus"), value: knowledgeBase.sync_status },
    { label: t("contextManagement.lifecycle.summaryLabels.documents"), value: knowledgeBase.document_count },
    { label: t("contextManagement.lifecycle.summaryLabels.bindings"), value: knowledgeBase.binding_count ?? 0 },
    { label: t("contextManagement.lifecycle.summaryLabels.eligibility"), value: eligibility, tone: knowledgeBase.eligible_for_binding ? "success" : "warning" },
    { label: t("contextManagement.lifecycle.summaryLabels.provider"), value: backingProvider },
    { label: t("contextManagement.lifecycle.summaryLabels.embeddingProvider"), value: embeddingProvider },
    { label: t("contextManagement.lifecycle.summaryLabels.embeddingResource"), value: embeddingResource },
  ];

  if (knowledgeBase.last_sync_error) {
    rows.push({
      label: t("contextManagement.lifecycle.summaryLabels.lastError"),
      value: knowledgeBase.last_sync_error,
      tone: "danger",
    });
  }

  return rows;
}
