import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { THEME_COLOR_OVERRIDES_STORAGE_KEY, THEME_STORAGE_KEY } from "./theme";

function ThemeConsumer(): JSX.Element {
  const {
    theme,
    setTheme,
    applyColorOverrides,
    resetColorOverrides,
    allColorOverrides,
    getEffectiveColors,
    themeFamily,
    themePreset,
    themeFamilies,
  } = useTheme();

  return (
    <div>
      <p data-testid="theme-value">{theme}</p>
      <p data-testid="theme-family">{themeFamily.id}</p>
      <p data-testid="theme-preset">{themePreset.presetId}</p>
      <p data-testid="theme-family-count">{String(themeFamilies.length)}</p>
      <button type="button" onClick={() => setTheme("default-day")}>default-day</button>
      <button type="button" onClick={() => setTheme("default-night")}>default-night</button>
      <button type="button" onClick={() => setTheme("retro-terminal")}>retro-terminal</button>
      <button type="button" onClick={() => applyColorOverrides({ "--bg-canvas": "#123456" })}>apply-color-a</button>
      <button type="button" onClick={() => applyColorOverrides({ "--bg-canvas": "#654321" })}>apply-color-b</button>
      <button type="button" onClick={resetColorOverrides}>reset</button>
      <p data-testid="default-day-effective">{getEffectiveColors("default-day")["--bg-canvas"]}</p>
      <p data-testid="default-night-effective">{getEffectiveColors("default-night")["--bg-canvas"]}</p>
      <p data-testid="retro-terminal-effective">{getEffectiveColors("retro-terminal")["--bg-canvas"]}</p>
      <p data-testid="all-overrides">{JSON.stringify(allColorOverrides)}</p>
    </div>
  );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.removeAttribute("data-theme-family");
  });

  it("applies saved theme to dom and localStorage", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "retro-terminal");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    expect(screen.getByTestId("theme-value")).toHaveTextContent("retro-terminal");
    expect(screen.getByTestId("theme-family")).toHaveTextContent("retro");
    expect(screen.getByTestId("theme-preset")).toHaveTextContent("terminal");
    expect(document.documentElement.getAttribute("data-theme")).toBe("retro-terminal");
    expect(document.documentElement.getAttribute("data-theme-family")).toBe("retro");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("retro-terminal");
  });

  it("normalizes legacy storage values and persists the mapped preset", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    expect(screen.getByTestId("theme-value")).toHaveTextContent("default-night");
    expect(document.documentElement.getAttribute("data-theme")).toBe("default-night");
    expect(document.documentElement.getAttribute("data-theme-family")).toBe("default");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("default-night");
  });

  it("switches presets and keeps storage in sync", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "default-day");
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "retro-terminal" }));

    expect(screen.getByTestId("theme-value")).toHaveTextContent("retro-terminal");
    expect(document.documentElement.getAttribute("data-theme")).toBe("retro-terminal");
    expect(document.documentElement.getAttribute("data-theme-family")).toBe("retro");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("retro-terminal");
  });

  it("keeps preset overrides isolated and persists all selected presets", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "apply-color-a" }));
    expect(screen.getByTestId("default-day-effective")).toHaveTextContent("#123456");
    expect(screen.getByTestId("default-night-effective")).toHaveTextContent("#08111e");
    expect(screen.getByTestId("retro-terminal-effective")).toHaveTextContent("#08140d");

    await user.click(screen.getByRole("button", { name: "default-night" }));
    await user.click(screen.getByRole("button", { name: "apply-color-b" }));
    await user.click(screen.getByRole("button", { name: "retro-terminal" }));
    await user.click(screen.getByRole("button", { name: "apply-color-a" }));
    expect(screen.getByTestId("default-night-effective")).toHaveTextContent("#654321");
    expect(screen.getByTestId("default-day-effective")).toHaveTextContent("#123456");
    expect(screen.getByTestId("retro-terminal-effective")).toHaveTextContent("#123456");

    const storedRaw = window.localStorage.getItem(THEME_COLOR_OVERRIDES_STORAGE_KEY);
    expect(storedRaw).not.toBeNull();
    const stored = JSON.parse(storedRaw ?? "{}");
    expect(stored["default-day"]["--bg-canvas"]).toBe("#123456");
    expect(stored["default-night"]["--bg-canvas"]).toBe("#654321");
    expect(stored["retro-terminal"]["--bg-canvas"]).toBe("#123456");
  });

  it("reset only clears overrides for the active theme", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "apply-color-a" }));
    await user.click(screen.getByRole("button", { name: "default-night" }));
    await user.click(screen.getByRole("button", { name: "apply-color-b" }));
    await user.click(screen.getByRole("button", { name: "retro-terminal" }));
    await user.click(screen.getByRole("button", { name: "apply-color-a" }));

    await user.click(screen.getByRole("button", { name: "default-day" }));
    await user.click(screen.getByRole("button", { name: "reset" }));
    expect(screen.getByTestId("default-day-effective")).toHaveTextContent("#ecf3fb");
    expect(screen.getByTestId("default-night-effective")).toHaveTextContent("#654321");
    expect(screen.getByTestId("retro-terminal-effective")).toHaveTextContent("#123456");
  });

  it("exposes family metadata for selector UIs", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    expect(screen.getByTestId("theme-family-count")).toHaveTextContent("2");
  });
});
