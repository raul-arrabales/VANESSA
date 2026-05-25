import { describe, expect, it } from "vitest";
import { executionTraceEntries, progressIndexFromTrace, runtimeDetailRows } from "./catalogExecutionTrace";

describe("catalogExecutionTrace", () => {
  it("normalizes runtime log entries and filters incomplete rows", () => {
    const entries = executionTraceEntries([
      { stage: "request_received", level: "info", message: "Accepted", details: { backend: "image_generation" } },
      { stage: "", level: "info", message: "missing stage" },
      { stage: "completed", level: "info", message: "" },
    ]);

    expect(entries).toEqual([
      {
        stage: "request_received",
        level: "info",
        message: "Accepted",
        details: { backend: "image_generation" },
      },
    ]);
  });

  it("maps backend trace stages onto progress indexes", () => {
    expect(progressIndexFromTrace([
      { stage: "request_received", level: "info", message: "Accepted" },
      { stage: "runtime_dispatched", level: "info", message: "Dispatched" },
    ])).toBe(2);
    expect(progressIndexFromTrace([])).toBeNull();
  });

  it("formats common detail values as display rows", () => {
    expect(runtimeDetailRows({
      backend: "image_generation",
      tasks: ["text_to_image"],
      has_image: true,
      nested: { status_code: 200 },
    })).toEqual([
      { key: "backend", value: "image_generation" },
      { key: "tasks", value: "text_to_image" },
      { key: "has_image", value: "yes" },
      { key: "nested", value: "{\"status_code\":200}" },
    ]);
  });
});
