import { describe, expect, it } from "vitest";
import { formatElapsedDuration } from "./timing";

describe("formatElapsedDuration", () => {
  it("formats sub-second durations in milliseconds", () => {
    expect(formatElapsedDuration(360, "en")).toBe("360 ms");
  });

  it("formats longer durations in seconds with one decimal", () => {
    expect(formatElapsedDuration(1250, "en")).toBe("1.3 s");
  });
});
