import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import PhosphorDisplay, { buildBannerFrame } from "./PhosphorDisplay";
import { ThemeProvider, useTheme } from "../theme/ThemeProvider";

const VANESSA_FRAME = [
  "#     #    #    #     # #######  #####   #####     #   ",
  "#     #   # #   ##    # #       #     # #     #   # #  ",
  "#     #  #   #  # #   # #       #       #        #   # ",
  "#     # #     # #  #  # #####    #####   #####  #     #",
  " #   #  ####### #   # # #             #       # #######",
  "  # #   #     # #    ## #       #     # #     # #     #",
  "   #    #     # #     # #######  #####   #####  #     #",
] as const;

function ThemeHarness(): JSX.Element {
  const { setTheme } = useTheme();

  return (
    <div>
      <PhosphorDisplay
        className="app-brand-display"
        label="VANESSA"
        frame={buildBannerFrame("VANESSA")}
        hoverMode="soft-glow"
      />
      <button type="button" onClick={() => setTheme("default-day")}>default-day</button>
      <button type="button" onClick={() => setTheme("retro-terminal")}>retro-terminal</button>
    </div>
  );
}

describe("PhosphorDisplay", () => {
  it("builds the stable banner frame for VANESSA", () => {
    const frame = buildBannerFrame("VANESSA");

    expect(frame).toEqual(VANESSA_FRAME);
    expect(frame).toHaveLength(7);
    expect(frame[0]).toHaveLength(55);
  });

  it("renders lit and dim cells from the frame while keeping an accessible label", () => {
    const frame = buildBannerFrame("VANESSA");

    const { container } = render(
      <h1>
        <PhosphorDisplay label="VANESSA" frame={frame} hoverMode="soft-glow" />
      </h1>,
    );

    const display = screen.getByTestId("phosphor-display");
    const litCells = frame.join("").replace(/ /g, "").length;
    const totalCells = frame.length * frame[0].length;

    expect(display).toBeVisible();
    expect(screen.getByRole("heading", { name: "VANESSA" })).toBeVisible();
    expect(container.querySelectorAll(".phosphor-display__cell--lit")).toHaveLength(litCells);
    expect(container.querySelectorAll(".phosphor-display__cell--dim")).toHaveLength(totalCells - litCells);
  });

  it("remains mounted while the theme family changes", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>,
    );

    expect(document.documentElement.getAttribute("data-theme-family")).toBe("default");
    expect(screen.getByTestId("phosphor-display")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "retro-terminal" }));

    expect(document.documentElement.getAttribute("data-theme")).toBe("retro-terminal");
    expect(document.documentElement.getAttribute("data-theme-family")).toBe("retro");
    expect(screen.getByTestId("phosphor-display")).toBeVisible();
  });
});
