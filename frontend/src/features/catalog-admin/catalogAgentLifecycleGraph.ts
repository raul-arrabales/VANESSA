import type { TFunction } from "i18next";
import type { CatalogAgent, CatalogAgentValidation } from "../../api/catalog";
import type { LifecycleGraphDefinition, LifecycleTransitionDefinition } from "../../components/LifecycleGraph";

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
  return {
    artifactType: "catalog-agent",
    states: CATALOG_AGENT_LIFECYCLE_STATE_IDS.map((stateId, index) => ({
      id: stateId,
      label: t(`catalogControl.agents.lifecycle.states.${stateId}`),
      x: [90, 290, 490, 670][index],
      y: [90, 90, 90, 210][index],
    })),
    transitions: CATALOG_AGENT_LIFECYCLE_TRANSITIONS.map((transition) => ({
      ...transition,
      label: t(`catalogControl.agents.lifecycle.transitions.${transition.from}.${transition.to}`),
    })),
  };
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

export function getCatalogAgentLifecycleSummary(
  t: TFunction<"common">,
  agent: CatalogAgent,
  validationResult?: CatalogAgentValidation,
): string {
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
  ].join(", ");

  return t("catalogControl.agents.lifecycle.summary", {
    kind,
    publishStatus,
    validationStatus,
    model: agent.spec.default_model_ref ?? t("platformControl.summary.none"),
    toolCount: agent.spec.tool_refs.length,
    mcpCount: agent.spec.mcp_server_refs?.length ?? 0,
    runtimeConstraints,
  });
}
