import { expect } from "vitest";
import type { LifecycleGraphDefinition, LifecycleCounts, LifecycleTransitionDefinition } from "../components/lifecycle-graph";

export function expectLifecycleDefinition(
  definition: LifecycleGraphDefinition,
  options: {
    stateIds: readonly string[];
    transitions: readonly LifecycleTransitionDefinition[];
    i18nBase: string;
    transitionLabelKey?: (transition: LifecycleTransitionDefinition) => string;
  },
): void {
  expect(definition.states.map((state) => state.id)).toEqual([...options.stateIds]);
  expect(definition.transitions).toEqual(
    options.transitions.map((transition) => ({
      ...transition,
      label: options.transitionLabelKey?.(transition) ?? `${options.i18nBase}.transitions.${transition.from}.${transition.to}`,
    })),
  );
}

export function expectTerminalStateUncounted(counts: LifecycleCounts, stateId = "deleted"): void {
  expect(counts.byState[stateId]).toBe(0);
}
