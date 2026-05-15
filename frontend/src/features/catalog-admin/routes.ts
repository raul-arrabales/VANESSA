export type CatalogControlSection = "overview" | "tools" | "agents" | "mcp";
export type CatalogToolsView = "tools" | "create" | "test";
export type CatalogAgentsView = "agents" | "user-agents" | "create";
export type CatalogMcpView = "registry" | "create" | "edit";

export const CATALOG_CONTROL_NAV_ITEMS: ReadonlyArray<{
  id: CatalogControlSection;
  labelKey: string;
}> = [
  { id: "overview", labelKey: "catalogControl.navigation.overview" },
  { id: "tools", labelKey: "catalogControl.navigation.tools" },
  { id: "mcp", labelKey: "catalogControl.navigation.mcp" },
  { id: "agents", labelKey: "catalogControl.navigation.agents" },
];

export function resolveCatalogControlSection(value: string | null): CatalogControlSection {
  if (value === "tools" || value === "agents" || value === "overview" || value === "mcp") {
    return value;
  }
  return "overview";
}

export function resolveCatalogMcpView(value: string | null): CatalogMcpView {
  if (value === "create" || value === "edit" || value === "registry") {
    return value;
  }
  return "registry";
}

export function resolveCatalogMcpServerId(value: string | null): string {
  return String(value ?? "").trim();
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
  view?: CatalogToolsView | CatalogAgentsView | CatalogMcpView,
  options: { toolId?: string; mcpServerId?: string } = {},
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
  if (section === "mcp" && view === "edit" && options.mcpServerId) {
    params.set("id", options.mcpServerId);
  }
  return `/control/catalog?${params.toString()}`;
}
