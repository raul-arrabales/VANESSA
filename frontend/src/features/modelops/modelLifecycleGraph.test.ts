import { describe, expect, it } from "vitest";
import { expectLifecycleDefinition } from "../../test/lifecycleGraphAssertions";
import { createModelLifecycleGraphDefinition, MODEL_LIFECYCLE_STATE_IDS, MODEL_LIFECYCLE_TRANSITIONS } from "./modelLifecycleGraph";

const t = ((key: string) => key) as never;

describe("model lifecycle graph definition", () => {
  it("includes the model lifecycle states and transitions", () => {
    const definition = createModelLifecycleGraphDefinition(t);

    expectLifecycleDefinition(definition, {
      stateIds: MODEL_LIFECYCLE_STATE_IDS,
      transitions: MODEL_LIFECYCLE_TRANSITIONS,
      i18nBase: "modelOps.lifecycle",
      transitionLabelKey: (transition) => `modelOps.lifecycle.transitions.${transition.from}_${transition.to}`,
    });
    expect(MODEL_LIFECYCLE_TRANSITIONS).toEqual([
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
    ]);
  });
});
