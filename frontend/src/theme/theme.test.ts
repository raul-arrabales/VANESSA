import { describe, expect, it } from "vitest";
import { getToggledTheme, resolveInitialTheme } from "./theme";

describe("theme helpers", () => {
  it("uses system preference when storage is empty", () => {
    expect(resolveInitialTheme(null, true)).toBe("dark");
    expect(resolveInitialTheme(null, false)).toBe("light");
  });

  it("uses saved storage value when available", () => {
    expect(resolveInitialTheme("dark", false)).toBe("dark");
    expect(resolveInitialTheme("light", true)).toBe("light");
  });

  it("toggles between light and dark", () => {
    expect(getToggledTheme("light")).toBe("dark");
    expect(getToggledTheme("dark")).toBe("light");
  });
});
