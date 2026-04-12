export type ModelOpsWorkspaceSection =
  | "overview"
  | "catalog"
  | "cloud"
  | "access"
  | "local-register";

type ModelOpsWorkspaceNavItem = {
  section: ModelOpsWorkspaceSection;
  path: string;
  labelKey: string;
  minimumRole?: "admin" | "superadmin";
};

export const MODEL_OPS_WORKSPACE_NAV_ITEMS: ModelOpsWorkspaceNavItem[] = [
  {
    section: "overview",
    path: "/control/models",
    labelKey: "nav.models",
  },
  {
    section: "catalog",
    path: "/control/models/catalog",
    labelKey: "nav.modelsCatalog",
  },
  {
    section: "cloud",
    path: "/control/models/cloud/register",
    labelKey: "nav.modelsCloudRegister",
  },
  {
    section: "local-register",
    path: "/control/models/local/register",
    labelKey: "nav.modelsLocalRegister",
    minimumRole: "superadmin",
  },
  {
    section: "access",
    path: "/control/models/access",
    labelKey: "nav.modelsAccess",
    minimumRole: "admin",
  },
];

export function canAccessModelOpsWorkspaceSection(
  role: string | null | undefined,
  minimumRole?: "admin" | "superadmin",
): boolean {
  if (!minimumRole) {
    return true;
  }
  if (minimumRole === "admin") {
    return role === "admin" || role === "superadmin";
  }
  return role === "superadmin";
}

export function isModelOpsWorkspacePathActive(currentPathname: string, itemPath: string): boolean {
  return itemPath === "/control/models"
    ? currentPathname === itemPath
    : currentPathname === itemPath || currentPathname.startsWith(`${itemPath}/`);
}
