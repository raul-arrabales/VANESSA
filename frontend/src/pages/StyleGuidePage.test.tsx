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
      <button type="button" onClick={() => setTheme("light")}>switch-light</button>
      <button type="button" onClick={() => setTheme("dark")}>switch-dark</button>
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

    await user.click(screen.getByRole("button", { name: "switch-dark" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#08111e");
    });
  });

  it("discards unsaved edits on theme switch", async () => {
    const user = renderStyleGuide();

    const lightInput = getTokenHexInput("--bg-canvas");
    await user.clear(lightInput);
    await user.type(lightInput, "#abcdef");

    await user.click(screen.getByRole("button", { name: "switch-dark" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#08111e");
    });

    await user.click(screen.getByRole("button", { name: "switch-light" }));
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

    await user.click(screen.getByRole("button", { name: "switch-dark" }));
    const darkInput = getTokenHexInput("--bg-canvas");
    await user.clear(darkInput);
    await user.type(darkInput, "#222222");
    await user.click(screen.getByRole("button", { name: "Apply theme changes" }));

    await user.click(screen.getByRole("button", { name: "switch-light" }));
    await user.click(screen.getByRole("button", { name: "Reset current theme" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#ecf3fb");
    });

    await user.click(screen.getByRole("button", { name: "switch-dark" }));
    await waitFor(() => {
      expect(getTokenHexInput("--bg-canvas").value).toBe("#222222");
    });
  });
});
