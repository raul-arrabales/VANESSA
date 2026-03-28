import { describe, expect, it } from "vitest";
import {
  DEFAULT_DAY_THEME_ID,
  DEFAULT_NIGHT_THEME_ID,
  getDefaultThemeId,
  getThemeFamilyPresets,
  getThemePreset,
  normalizeStoredTheme,
  resolveInitialTheme,
} from "./theme";

describe("theme helpers", () => {
  it("uses system preference when storage is empty", () => {
    expect(resolveInitialTheme(null, true)).toBe(DEFAULT_NIGHT_THEME_ID);
    expect(resolveInitialTheme(null, false)).toBe(DEFAULT_DAY_THEME_ID);
  });

  it("uses saved storage value when available", () => {
    expect(resolveInitialTheme("retro-terminal", false)).toBe("retro-terminal");
    expect(resolveInitialTheme("default-day", true)).toBe(DEFAULT_DAY_THEME_ID);
  });

  it("normalizes legacy light and dark storage values", () => {
    expect(normalizeStoredTheme("light")).toBe(DEFAULT_DAY_THEME_ID);
    expect(normalizeStoredTheme("dark")).toBe(DEFAULT_NIGHT_THEME_ID);
  });

  it("exposes family presets and theme metadata", () => {
    expect(getDefaultThemeId()).toBe(DEFAULT_DAY_THEME_ID);
    expect(getThemeFamilyPresets("default").map((preset) => preset.id)).toEqual(["default-day", "default-night"]);
    expect(getThemePreset("retro-terminal").familyId).toBe("retro");
  });
});
