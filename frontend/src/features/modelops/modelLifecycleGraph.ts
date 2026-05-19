import type { TFunction } from "i18next";
import type { ManagedModel } from "../../api/modelops/types";
import { buildLifecycleGraphDefinition, type LifecycleGraphDefinition } from "../../components/LifecycleGraph";

export const MODEL_LIFECYCLE_STATE_IDS = [
  "created",
  "registered",
  "validated",
  "active",
  "inactive",
  "unregistered",
  "deleted",
] as const;

export const MODEL_LIFECYCLE_TRANSITIONS = [
  { from: "created", to: "registered" },
  { from: "unregistered", to: "registered" },
  { from: "registered", to: "validated" },
  { from: "validated", to: "active" },
  { from: "active", to: "inactive" },
  { from: "inactive", to: "active" },
  { from: "validated", to: "unregistered" },
  { from: "inactive", to: "unregistered" },
  { from: "registered", to: "unregistered" },
  { from: "unregistered", to: "deleted" },
] as const;

const MODEL_LIFECYCLE_STATE_POSITIONS: Record<(typeof MODEL_LIFECYCLE_STATE_IDS)[number], { x: number; y: number }> = {
  created: { x: 90, y: 82 },
  registered: { x: 245, y: 82 },
  validated: { x: 400, y: 82 },
  active: { x: 555, y: 82 },
  inactive: { x: 555, y: 208 },
  unregistered: { x: 245, y: 208 },
  deleted: { x: 90, y: 208 },
};

export function createModelLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return buildLifecycleGraphDefinition(t, {
    artifactType: "model",
    stateIds: MODEL_LIFECYCLE_STATE_IDS,
    i18nBase: "modelOps.lifecycle",
    positions: MODEL_LIFECYCLE_STATE_POSITIONS,
    transitions: MODEL_LIFECYCLE_TRANSITIONS,
    transitionLabelKey: (transition) => `modelOps.lifecycle.transitions.${transition.from}_${transition.to}`,
  });
}

export function getModelLifecycleState(model: ManagedModel): string | null | undefined {
  return model.lifecycle_state;
}

export function getModelValidationLifecycleSummary(t: TFunction<"common">, model: ManagedModel): string {
  if (model.is_validation_current && model.last_validation_status === "success") {
    return t("modelOps.lifecycle.validation.current");
  }
  if (model.last_validation_status === "failure") {
    return t("modelOps.lifecycle.validation.failed");
  }
  if (model.last_validation_status === "success") {
    return t("modelOps.lifecycle.validation.stale");
  }
  return t("modelOps.lifecycle.validation.pending");
}
