import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import VanessaLogo from "./VanessaLogo";
import { ThemeProvider, useTheme } from "../theme/ThemeProvider";

function ThemeHarness(): JSX.Element {
  const { setTheme } = useTheme();

  return (
    <div>
      <VanessaLogo className="app-logo" />
      <button type="button" onClick={() => setTheme("default-day")}>default-day</button>
      <button type="button" onClick={() => setTheme("retro-terminal")}>retro-terminal</button>
    </div>
  );
}

describe("VanessaLogo", () => {
  it("renders the adaptive svg mark with reusable classes", () => {
    render(<VanessaLogo className="app-logo" size={64} />);

    const logo = screen.getByTestId("app-logo");
    expect(logo.tagName.toLowerCase()).toBe("svg");
    expect(logo).toHaveAttribute("viewBox", "0 0 64 64");
    expect(logo).toHaveClass("app-logo");
    expect(logo.querySelector(".vanessa-logo__orbit")).not.toBeNull();
    expect(logo.querySelector(".vanessa-logo__vector")).not.toBeNull();
    expect(logo.querySelector(".vanessa-logo__core")).not.toBeNull();
  });

  it("remains present while theme context changes between default and retro", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>,
    );

    const logo = screen.getByTestId("app-logo");
    expect(document.documentElement.getAttribute("data-theme-family")).toBe("default");
    expect(logo).toBeVisible();

    await user.click(screen.getByRole("button", { name: "retro-terminal" }));
    expect(document.documentElement.getAttribute("data-theme")).toBe("retro-terminal");
    expect(document.documentElement.getAttribute("data-theme-family")).toBe("retro");
    expect(screen.getByTestId("app-logo")).toBeVisible();
  });
});
