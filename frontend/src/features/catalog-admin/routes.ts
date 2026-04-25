export type CatalogControlSection = "overview" | "tools" | "agents";
export type CatalogToolsView = "tools" | "create" | "test";
export type CatalogAgentsView = "agents" | "user-agents" | "create";

export const CATALOG_CONTROL_NAV_ITEMS: ReadonlyArray<{
  id: CatalogControlSection;
  labelKey: string;
}> = [
  { id: "overview", labelKey: "catalogControl.navigation.overview" },
  { id: "tools", labelKey: "catalogControl.navigation.tools" },
  { id: "agents", labelKey: "catalogControl.navigation.agents" },
];

export function resolveCatalogControlSection(value: string | null): CatalogControlSection {
  if (value === "tools" || value === "agents" || value === "overview") {
    return value;
  }
  return "overview";
}

export function resolveCatalogToolsView(value: string | null): CatalogToolsView {
  if (value === "create" || value === "tools" || value === "test") {
    return value;
  }
  return "tools";
}

export function resolveCatalogToolId(value: string | null): string {
  return String(value ?? "").trim();
}

export function resolveCatalogAgentsView(value: string | null): CatalogAgentsView {
  if (value === "create" || value === "agents" || value === "user-agents") {
    return value;
  }
  return "agents";
}

export function buildCatalogControlUrl(
  section: CatalogControlSection,
  view?: CatalogToolsView | CatalogAgentsView,
  options: { toolId?: string } = {},
): string {
  if (section === "overview") {
    return "/control/catalog";
  }

  const params = new URLSearchParams();
  params.set("section", section);
  if (view) {
    params.set("view", view);
  }
  if (section === "tools" && view === "test" && options.toolId) {
    params.set("toolId", options.toolId);
  }
  return `/control/catalog?${params.toString()}`;
}
