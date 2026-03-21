import type { JSX } from "react";
import type { Role } from "../auth/types";
import AiPage from "../pages/AiPage";
import AdminApprovalsPage from "../pages/AdminApprovalsPage";
import BackendHealthPage from "../pages/BackendHealthPage";
import ChatbotPage from "../pages/ChatbotPage";
import CatalogControlPage from "../pages/CatalogControlPage";
import ControlPage from "../pages/ControlPage";
import HomePage from "../pages/HomePage";
import KnowledgeChatPage from "../pages/KnowledgeChatPage";
import LoginPage from "../pages/LoginPage";
import PlatformControlPage from "../pages/PlatformControlPage";
import QuoteManagementPage from "../pages/QuoteManagementPage";
import RegisterPage from "../pages/RegisterPage";
import SettingsPage from "../pages/SettingsPage";
import StyleGuidePage from "../pages/StyleGuidePage";
import CloudModelRegisterPage from "../features/modelops/pages/CloudModelRegisterPage";
import LocalArtifactsPage from "../features/modelops/pages/LocalArtifactsPage";
import LocalModelRegisterPage from "../features/modelops/pages/LocalModelRegisterPage";
import ModelAccessManagementPage from "../features/modelops/pages/ModelAccessManagementPage";
import ModelCatalogPage from "../features/modelops/pages/ModelCatalogPage";
import ModelDetailPage from "../features/modelops/pages/ModelDetailPage";
import ModelOpsHomePage from "../features/modelops/pages/ModelOpsHomePage";

export type AppRouteSection = "public" | "settings" | "control" | "ai";
export type AppRouteNavGroup = "primary" | "userMenu";
export type AppRouteAudience = "guest" | "authenticated" | "all";

export type AppRouteDefinition = {
  id: string;
  path: string;
  titleKey: string;
  breadcrumbTitleKey?: string;
  section: AppRouteSection;
  showInNav: boolean;
  showInBreadcrumbs: boolean;
  requiresAuth: boolean;
  minimumRole?: Role;
  guestOnly?: boolean;
  navGroup?: AppRouteNavGroup;
  navAudience?: AppRouteAudience;
  element: JSX.Element;
};

export const removedLegacyPaths = [
  "/welcome/user",
  "/welcome/admin",
  "/welcome/superadmin",
  "/welcome/superadmin/models",
  "/admin/approvals",
  "/backend-health",
  "/settings/model-access",
  "/chat",
] as const;

export const appRoutes: AppRouteDefinition[] = [
  {
    id: "home",
    path: "/",
    titleKey: "nav.home",
    section: "public",
    showInNav: true,
    showInBreadcrumbs: true,
    requiresAuth: false,
    navGroup: "primary",
    navAudience: "guest",
    element: <HomePage />,
  },
  {
    id: "login",
    path: "/login",
    titleKey: "nav.login",
    section: "public",
    showInNav: true,
    showInBreadcrumbs: true,
    requiresAuth: false,
    guestOnly: true,
    navGroup: "userMenu",
    navAudience: "guest",
    element: <LoginPage />,
  },
  {
    id: "register",
    path: "/register",
    titleKey: "nav.register",
    section: "public",
    showInNav: true,
    showInBreadcrumbs: true,
    requiresAuth: false,
    guestOnly: true,
    navGroup: "userMenu",
    navAudience: "guest",
    element: <RegisterPage />,
  },
  {
    id: "settings",
    path: "/settings",
    titleKey: "nav.settings",
    section: "settings",
    showInNav: true,
    showInBreadcrumbs: true,
    requiresAuth: true,
    navGroup: "userMenu",
    navAudience: "authenticated",
    element: <SettingsPage />,
  },
  {
    id: "settings-design",
    path: "/settings/design",
    titleKey: "nav.designEditor",
    section: "settings",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <StyleGuidePage />,
  },
  {
    id: "control",
    path: "/control",
    titleKey: "nav.control",
    breadcrumbTitleKey: "nav.controlPanel",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <ControlPage />,
  },
  {
    id: "control-approvals",
    path: "/control/approvals",
    titleKey: "nav.approvals",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "admin",
    element: <AdminApprovalsPage />,
  },
  {
    id: "control-quotes",
    path: "/control/quotes",
    titleKey: "nav.quotes",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "admin",
    element: <QuoteManagementPage />,
  },
  {
    id: "control-catalog",
    path: "/control/catalog",
    titleKey: "nav.catalog",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "superadmin",
    element: <CatalogControlPage />,
  },
  {
    id: "control-system-health",
    path: "/control/system-health",
    titleKey: "nav.systemHealth",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "superadmin",
    element: <BackendHealthPage />,
  },
  {
    id: "control-platform",
    path: "/control/platform",
    titleKey: "nav.platform",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "superadmin",
    element: <PlatformControlPage />,
  },
  {
    id: "control-models",
    path: "/control/models",
    titleKey: "nav.models",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <ModelOpsHomePage />,
  },
  {
    id: "control-models-catalog",
    path: "/control/models/catalog",
    titleKey: "nav.modelsCatalog",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <ModelCatalogPage />,
  },
  {
    id: "control-models-cloud-register",
    path: "/control/models/cloud/register",
    titleKey: "nav.modelsCloudRegister",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <CloudModelRegisterPage />,
  },
  {
    id: "control-models-local-register",
    path: "/control/models/local/register",
    titleKey: "nav.modelsLocalRegister",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "superadmin",
    element: <LocalModelRegisterPage />,
  },
  {
    id: "control-models-local-artifacts",
    path: "/control/models/local/artifacts",
    titleKey: "nav.modelsLocalArtifacts",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "superadmin",
    element: <LocalArtifactsPage />,
  },
  {
    id: "control-models-access",
    path: "/control/models/access",
    titleKey: "nav.modelsAccess",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "admin",
    element: <ModelAccessManagementPage />,
  },
  {
    id: "control-models-detail",
    path: "/control/models/:modelId",
    titleKey: "nav.modelDetail",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <ModelDetailPage />,
  },
  {
    id: "ai",
    path: "/ai",
    titleKey: "nav.ai",
    section: "ai",
    showInNav: true,
    showInBreadcrumbs: true,
    requiresAuth: true,
    navGroup: "primary",
    navAudience: "authenticated",
    element: <AiPage />,
  },
  {
    id: "ai-chat",
    path: "/ai/chat",
    titleKey: "nav.chat",
    section: "ai",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <ChatbotPage />,
  },
  {
    id: "ai-knowledge",
    path: "/ai/knowledge",
    titleKey: "nav.knowledge",
    section: "ai",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <KnowledgeChatPage />,
  },
];

function isRoutePrefix(pathname: string, routePath: string): boolean {
  if (routePath === "/") {
    return pathname === "/";
  }
  return pathname === routePath || pathname.startsWith(`${routePath}/`);
}

export function getBreadcrumbRoutes(pathname: string): AppRouteDefinition[] {
  return appRoutes
    .filter((route) => route.showInBreadcrumbs && isRoutePrefix(pathname, route.path))
    .sort((left, right) => left.path.length - right.path.length);
}

export function getNavRoutes(
  navGroup: AppRouteNavGroup,
  options: {
    isAuthenticated: boolean;
  },
): AppRouteDefinition[] {
  const { isAuthenticated } = options;
  return appRoutes.filter((route) => {
    if (!route.showInNav || route.navGroup !== navGroup) {
      return false;
    }
    if (route.navAudience === "guest") {
      return !isAuthenticated;
    }
    if (route.navAudience === "authenticated") {
      return isAuthenticated;
    }
    return true;
  });
}
