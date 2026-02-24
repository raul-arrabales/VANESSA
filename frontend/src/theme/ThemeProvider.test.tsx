import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { THEME_COLOR_OVERRIDES_STORAGE_KEY, THEME_STORAGE_KEY } from "./theme";

function ThemeConsumer(): JSX.Element {
  const {
    theme,
    toggleTheme,
    setTheme,
    applyColorOverrides,
    resetColorOverrides,
    allColorOverrides,
    getEffectiveColors,
  } = useTheme();

  return (
    <div>
      <p data-testid="theme-value">{theme}</p>
      <button type="button" onClick={toggleTheme}>toggle</button>
      <button type="button" onClick={() => setTheme("light")}>light</button>
      <button type="button" onClick={() => setTheme("dark")}>dark</button>
      <button type="button" onClick={() => applyColorOverrides({ "--bg-canvas": "#123456" })}>apply-color-a</button>
      <button type="button" onClick={() => applyColorOverrides({ "--bg-canvas": "#654321" })}>apply-color-b</button>
      <button type="button" onClick={resetColorOverrides}>reset</button>
      <p data-testid="light-effective">{getEffectiveColors("light")["--bg-canvas"]}</p>
      <p data-testid="dark-effective">{getEffectiveColors("dark")["--bg-canvas"]}</p>
      <p data-testid="all-overrides">{JSON.stringify(allColorOverrides)}</p>
    </div>
  );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("applies saved theme to dom and localStorage", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    expect(screen.getByTestId("theme-value")).toHaveTextContent("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("toggles theme and keeps storage in sync", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "toggle" }));

    expect(screen.getByTestId("theme-value")).toHaveTextContent("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("keeps light and dark overrides isolated and persists both", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "apply-color-a" }));
    expect(screen.getByTestId("light-effective")).toHaveTextContent("#123456");
    expect(screen.getByTestId("dark-effective")).toHaveTextContent("#08111e");

    await user.click(screen.getByRole("button", { name: "dark" }));
    await user.click(screen.getByRole("button", { name: "apply-color-b" }));
    expect(screen.getByTestId("dark-effective")).toHaveTextContent("#654321");
    expect(screen.getByTestId("light-effective")).toHaveTextContent("#123456");

    const storedRaw = window.localStorage.getItem(THEME_COLOR_OVERRIDES_STORAGE_KEY);
    expect(storedRaw).not.toBeNull();
    const stored = JSON.parse(storedRaw ?? "{}");
    expect(stored.light["--bg-canvas"]).toBe("#123456");
    expect(stored.dark["--bg-canvas"]).toBe("#654321");
  });

  it("reset only clears overrides for the active theme", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "apply-color-a" }));
    await user.click(screen.getByRole("button", { name: "dark" }));
    await user.click(screen.getByRole("button", { name: "apply-color-b" }));

    await user.click(screen.getByRole("button", { name: "light" }));
    await user.click(screen.getByRole("button", { name: "reset" }));
    expect(screen.getByTestId("light-effective")).toHaveTextContent("#ecf3fb");
    expect(screen.getByTestId("dark-effective")).toHaveTextContent("#654321");
  });
});
