import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import OptionCardGrid, { type OptionCardItem } from "./OptionCardGrid";

const items: OptionCardItem[] = [
  {
    id: "profile",
    title: "View your profile",
    description: "Confirm identity, account status, and role information.",
    to: "/settings",
    icon: "profile",
  },
  {
    id: "approvals",
    title: "Process user approvals",
    description: "Use admin approval workflow to activate pending accounts.",
    to: "/admin/approvals",
    icon: "approvals",
  },
];

describe("OptionCardGrid", () => {
  it("renders cards as full-link tiles with icons", () => {
    const { container } = render(
      <MemoryRouter>
        <OptionCardGrid items={items} ariaLabel="Available actions" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("list", { name: "Available actions" })).toBeVisible();
    expect(screen.getByRole("link", { name: "View your profile" })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: "Process user approvals" })).toHaveAttribute("href", "/admin/approvals");
    expect(container.querySelectorAll(".option-card-icon svg")).toHaveLength(items.length);
  });

  it("supports keyboard focus on card links", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <OptionCardGrid items={items} ariaLabel="Available actions" />
      </MemoryRouter>,
    );

    await user.tab();
    expect(screen.getByRole("link", { name: "View your profile" })).toHaveFocus();
  });
});
