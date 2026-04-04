import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MONOGRAM_FRAME } from "./brandFrames";
import VanessaBrand from "./VanessaBrand";

describe("VanessaBrand", () => {
  it("renders the compact monogram using the denser 13-cell banner-style V", () => {
    const { container } = render(
      <VanessaBrand variant="monogram" label="VANESSA" />,
    );
    const litCells = MONOGRAM_FRAME.join("").replace(/ /g, "").length;
    const totalCells = MONOGRAM_FRAME.join("").length;

    expect(screen.getByTestId("vanessa-monogram")).toBeVisible();
    expect(screen.getByText("VANESSA", { selector: ".sr-only" })).toBeVisible();
    expect(container.querySelectorAll(".vanessa-monogram__row")).toHaveLength(MONOGRAM_FRAME.length);
    expect(container.querySelectorAll(".vanessa-monogram__cell--lit")).toHaveLength(litCells);
    expect(container.querySelectorAll(".vanessa-monogram__cell--dim")).toHaveLength(totalCells - litCells);
  });

  it("keeps the full wordmark variant unchanged", () => {
    const { container } = render(
      <h1>
        <VanessaBrand variant="wordmark" label="VANESSA" />
      </h1>,
    );

    expect(screen.getByRole("heading", { name: "VANESSA" })).toBeVisible();
    expect(screen.getByTestId("phosphor-display")).toBeVisible();
    expect(container.querySelectorAll(".phosphor-display__row")).toHaveLength(7);
    expect(container.querySelectorAll(".phosphor-display__cell--lit").length).toBeGreaterThan(13);
  });
});
