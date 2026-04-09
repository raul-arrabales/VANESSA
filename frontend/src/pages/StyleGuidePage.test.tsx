import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { useTheme, ThemeProvider } from "../theme/ThemeProvider";
import StyleGuidePage from "./StyleGuidePage";

function ThemeModeControls(): JSX.Element {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <p data-testid="active-theme">{theme}</p>
      <button type="button" onClick={() => setTheme("default-day")}>switch-default-day</button>
      <button type="button" onClick={() => setTheme("default-night")}>switch-default-night</button>
      <button type="button" onClick={() => setTheme("retro-terminal")}>switch-retro-terminal</button>
    </div>
  );
}

function renderStyleGuide(): ReturnType<typeof userEvent.setup> {
  const user = userEvent.setup();
  render(
    <ThemeProvider>
      <ThemeModeControls />
      <StyleGuidePage />
    </ThemeProvider>,
  );
  return user;
}

function getTokenHexInput(token: string): HTMLInputElement {
  return screen.getByLabelText(`${token} hex value`) as HTMLInputElement;
}

describe("StyleGuidePage theme editor", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("applies changes only to the active theme", async () => {
    const user = renderStyleGuide();

    const bgCanvasInput = getTokenHexInput("--bg-canvas");
    await user.clear(bgCanvasInput);
    await user.type(bgCanvasInput, "#123456");
    await user.click(screen.getByRole("button", { name: "Apply theme changes" }));

    await user.click(screen.getByRole("button", { name: "switch-default-night" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#08111e");
    });
  });

  it("discards unsaved edits on theme switch", async () => {
    const user = renderStyleGuide();

    const lightInput = getTokenHexInput("--bg-canvas");
    await user.clear(lightInput);
    await user.type(lightInput, "#abcdef");

    await user.click(screen.getByRole("button", { name: "switch-retro-terminal" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#08140d");
    });

    await user.click(screen.getByRole("button", { name: "switch-default-day" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#ecf3fb");
    });
  });

  it("reset clears only active theme overrides", async () => {
    const user = renderStyleGuide();

    const lightInput = getTokenHexInput("--bg-canvas");
    await user.clear(lightInput);
    await user.type(lightInput, "#111111");
    await user.click(screen.getByRole("button", { name: "Apply theme changes" }));

    await user.click(screen.getByRole("button", { name: "switch-default-night" }));
    const darkInput = getTokenHexInput("--bg-canvas");
    await user.clear(darkInput);
    await user.type(darkInput, "#222222");
    await user.click(screen.getByRole("button", { name: "Apply theme changes" }));

    await user.click(screen.getByRole("button", { name: "switch-retro-terminal" }));
    const retroInput = getTokenHexInput("--bg-canvas");
    await user.clear(retroInput);
    await user.type(retroInput, "#333333");
    await user.click(screen.getByRole("button", { name: "Apply theme changes" }));

    await user.click(screen.getByRole("button", { name: "switch-default-day" }));
    await user.click(screen.getByRole("button", { name: "Reset current theme" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#ecf3fb");
    });

    await user.click(screen.getByRole("button", { name: "switch-default-night" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#222222");
    });

    await user.click(screen.getByRole("button", { name: "switch-retro-terminal" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#333333");
    });
  });

  it("documents nested panels without the repeated left rail", () => {
    renderStyleGuide();

    expect(screen.getByRole("heading", { name: "Panel hierarchy" })).toBeVisible();
    expect(screen.getByText(/Use the left rail only on the highest-level page or workspace panel\./)).toBeVisible();
    expect(screen.getByTestId("nested-panel-example")).toHaveClass("panel-nested");
  });
});
