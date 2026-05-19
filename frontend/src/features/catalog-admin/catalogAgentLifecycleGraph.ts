import type { TFunction } from "i18next";
import type { CatalogAgent, CatalogAgentValidation } from "../../api/catalog";
import { buildLifecycleGraphDefinition, type LifecycleGraphDefinition, type LifecycleSummaryRow, type LifecycleTransitionDefinition } from "../../components/lifecycle-graph";

export const CATALOG_AGENT_LIFECYCLE_STATE_IDS = [
  "draft",
  "published_unvalidated",
  "validation_failed",
  "ready",
] as const;

export type CatalogAgentLifecycleState = typeof CATALOG_AGENT_LIFECYCLE_STATE_IDS[number];

export const CATALOG_AGENT_LIFECYCLE_TRANSITIONS: LifecycleTransitionDefinition[] = [
  { from: "draft", to: "published_unvalidated" },
  { from: "published_unvalidated", to: "ready" },
  { from: "published_unvalidated", to: "validation_failed" },
  { from: "validation_failed", to: "published_unvalidated" },
  { from: "validation_failed", to: "ready" },
  { from: "published_unvalidated", to: "draft" },
  { from: "validation_failed", to: "draft" },
  { from: "ready", to: "draft" },
];

export function createCatalogAgentLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return buildLifecycleGraphDefinition(t, {
    artifactType: "catalog-agent",
    stateIds: CATALOG_AGENT_LIFECYCLE_STATE_IDS,
    i18nBase: "catalogControl.agents.lifecycle",
    positions: [
      { x: 90, y: 90 },
      { x: 290, y: 90 },
      { x: 490, y: 90 },
      { x: 670, y: 210 },
    ],
    transitions: CATALOG_AGENT_LIFECYCLE_TRANSITIONS,
  });
}

export function getCatalogAgentLifecycleState(
  agent: CatalogAgent,
  validationResult?: CatalogAgentValidation,
): CatalogAgentLifecycleState {
  if (!agent.published) {
    return "draft";
  }
  if (!validationResult) {
    return "published_unvalidated";
  }
  return validationResult.validation.valid ? "ready" : "validation_failed";
}

export function getCatalogAgentLifecycleSummaryRows(
  t: TFunction<"common">,
  agent: CatalogAgent,
  validationResult?: CatalogAgentValidation,
): LifecycleSummaryRow[] {
  const kind = agent.is_platform_agent || agent.agent_kind === "platform"
    ? t("catalogControl.agents.lifecycle.kind.platform")
    : t("catalogControl.agents.lifecycle.kind.user");
  const publishStatus = agent.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft");
  const validationStatus = validationResult
    ? validationResult.validation.valid
      ? t("catalogControl.agents.lifecycle.validation.valid")
      : t("catalogControl.agents.lifecycle.validation.invalid")
    : t("catalogControl.agents.lifecycle.validation.unvalidated");
  const runtimeConstraints = [
    agent.spec.runtime_constraints.internet_required
      ? t("catalogControl.agents.internetRequired")
      : t("catalogControl.agents.lifecycle.constraints.offline"),
    agent.spec.runtime_constraints.sandbox_required
      ? t("catalogControl.agents.sandboxRequired")
      : t("catalogControl.agents.lifecycle.constraints.noSandbox"),
  ];

  return [
    { label: t("catalogControl.agents.lifecycle.summaryLabels.kind"), value: kind },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.status"), value: publishStatus, tone: agent.published ? "active" : "required" },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.validation"), value: validationStatus, tone: validationResult?.validation.valid ? "success" : validationResult ? "danger" : "optional" },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.model"), value: agent.spec.default_model_ref ?? t("platformControl.summary.none") },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.tools"), value: agent.spec.tool_refs.length },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.mcpServers"), value: agent.spec.mcp_server_refs?.length ?? 0 },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.internet"), value: runtimeConstraints[0], tone: agent.spec.runtime_constraints.internet_required ? "optional" : "active" },
    { label: t("catalogControl.agents.lifecycle.summaryLabels.sandbox"), value: runtimeConstraints[1], tone: agent.spec.runtime_constraints.sandbox_required ? "optional" : "active" },
  ];
}
