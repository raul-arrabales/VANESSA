import type { TFunction } from "i18next";
import type {
  LifecycleCounts,
  LifecycleGraphDefinition,
  LifecycleGraphDefinitionOptions,
  LifecycleHighlight,
  LifecycleTransitionDefinition,
} from "./types";

function isPositionRecord<StateId extends string>(
  positions: LifecycleGraphDefinitionOptions<StateId>["positions"],
): positions is Partial<Record<StateId, { x: number; y: number }>> {
  return Boolean(positions) && !Array.isArray(positions);
}

export function lifecycleTransitionId(transition: LifecycleTransitionDefinition): string {
  return `${transition.from}->${transition.to}`;
}

export function buildLifecycleGraphDefinition<StateId extends string>(
  t: TFunction<"common">,
  options: LifecycleGraphDefinitionOptions<StateId>,
): LifecycleGraphDefinition {
  return {
    artifactType: options.artifactType,
    states: options.stateIds.map((stateId, index) => {
      const position = Array.isArray(options.positions)
        ? options.positions[index]
        : isPositionRecord(options.positions)
          ? options.positions[stateId]
          : undefined;
      return {
        id: stateId,
        label: t(`${options.i18nBase}.states.${stateId}`),
        ...position,
      };
    }),
    transitions: options.transitions.map((transition) => ({
      ...transition,
      label: t(options.transitionLabelKey?.(transition) ?? `${options.i18nBase}.transitions.${transition.from}.${transition.to}`),
    })),
  };
}

export function deriveLifecycleCounts<T>(
  items: T[],
  definition: LifecycleGraphDefinition,
  getState: (item: T) => string | null | undefined,
): LifecycleCounts {
  const knownStates = new Set(definition.states.map((state) => state.id));
  const byState = Object.fromEntries(definition.states.map((state) => [state.id, 0]));
  let unknown = 0;

  for (const item of items) {
    const state = String(getState(item) ?? "").trim().toLowerCase();
    if (knownStates.has(state)) {
      byState[state] += 1;
    } else {
      unknown += 1;
    }
  }

  return { byState, unknown };
}

export function resolveLifecycleHighlight<T>(
  item: T,
  definition: LifecycleGraphDefinition,
  getState: (item: T) => string | null | undefined,
): LifecycleHighlight {
  const currentState = String(getState(item) ?? "").trim().toLowerCase() || null;
  const knownStates = new Set(definition.states.map((state) => state.id));
  const resolvedCurrentState = currentState && knownStates.has(currentState) ? currentState : null;
  return {
    currentState: resolvedCurrentState,
    outgoingTransitions: new Set(
      definition.transitions
        .filter((transition) => transition.from === resolvedCurrentState)
        .map(lifecycleTransitionId),
    ),
  };
}
