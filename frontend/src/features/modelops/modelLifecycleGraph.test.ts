import { describe, expect, it } from "vitest";
import { MODEL_LIFECYCLE_STATE_IDS, MODEL_LIFECYCLE_TRANSITIONS } from "./modelLifecycleGraph";

describe("model lifecycle graph definition", () => {
  it("includes the model lifecycle states and transitions", () => {
    expect(MODEL_LIFECYCLE_STATE_IDS).toEqual([
      "created",
      "registered",
      "validated",
      "active",
      "inactive",
      "unregistered",
      "deleted",
    ]);
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
