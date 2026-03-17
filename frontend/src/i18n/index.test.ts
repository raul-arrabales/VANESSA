import { afterEach, describe, expect, it, vi } from "vitest";

describe("i18n initialization", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    window.localStorage.clear();
  });

  it("reuses the same initialization promise and instance", async () => {
    const i18nModule = await import("./index");

    const first = i18nModule.initI18n();
    const second = i18nModule.initI18n();

    expect(first).toBe(second);
    expect(await first).toBe(i18nModule.default);
  });

  it("normalizes en-US detection to the base en locale", async () => {
    window.localStorage.setItem("vanessa.locale", "en-US");
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const i18nModule = await import("./index");
    const instance = await i18nModule.initI18n();

    expect(instance.resolvedLanguage).toBe("en");
    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("Missing locale bundle for en-US/common"),
    );
  });
});
