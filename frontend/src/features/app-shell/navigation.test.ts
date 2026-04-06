import { describe, expect, it } from "vitest";
import {
  buildSidebarItems,
  buildTopBarPathItems,
  buildUserMenuItems,
  resolveConcreteRoutePath,
} from "./navigation";

const translate = (key: string): string => key;

describe("app-shell navigation", () => {
  it("resolves static and dynamic concrete route paths", () => {
    expect(resolveConcreteRoutePath("/control", "/control/models")).toBe("/control");
    expect(
      resolveConcreteRoutePath(
        "/control/context/:knowledgeBaseId/sources",
        "/control/context/45d38e20-f6fc-45bb-9e49-652a6c165bdd/sources",
      ),
    ).toBe("/control/context/45d38e20-f6fc-45bb-9e49-652a6c165bdd/sources");
  });

  it("builds top-bar path items with concrete paths and a single current segment", () => {
    const items = buildTopBarPathItems(
      "/control/context/45d38e20-f6fc-45bb-9e49-652a6c165bdd/sources",
      translate,
    );

    expect(items.map((item) => item.to)).toEqual([
      "/",
      "/control",
      "/control/context",
      "/control/context/45d38e20-f6fc-45bb-9e49-652a6c165bdd",
      "/control/context/45d38e20-f6fc-45bb-9e49-652a6c165bdd/sources",
    ]);
    expect(items.map((item) => item.isCurrent)).toEqual([false, false, false, false, true]);
  });

  it("builds sidebar and user-menu items from shared route metadata", () => {
    const sidebarItems = buildSidebarItems(
      "/control/models",
      { isAuthenticated: true, role: "superadmin" },
      translate,
    );
    const userMenuItems = buildUserMenuItems(true, translate);

    expect(sidebarItems.some((item) => item.to === "/control" && item.isActive)).toBe(true);
    expect(userMenuItems.some((item) => item.to === "/control")).toBe(true);
  });

  it("keeps guest auth sidebar items visually distinct when collapsed", () => {
    const sidebarItems = buildSidebarItems("/", { isAuthenticated: false }, translate);
    const loginItem = sidebarItems.find((item) => item.to === "/login");
    const registerItem = sidebarItems.find((item) => item.to === "/register");

    expect(loginItem?.icon).toBe("profile");
    expect(registerItem?.icon).toBe("register");
  });

  it("keeps Vanessa AI and playgrounds visually distinct when collapsed", () => {
    const sidebarItems = buildSidebarItems("/ai", { isAuthenticated: true }, translate);
    const vanessaItem = sidebarItems.find((item) => item.to === "/ai");
    const playgroundsItem = sidebarItems.find((item) => item.to === "/playgrounds");

    expect(vanessaItem?.icon).toBe("vanessa");
    expect(playgroundsItem?.icon).toBe("ai");
  });
});
