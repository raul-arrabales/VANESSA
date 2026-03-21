import { lazy, type JSX } from "react";
import type { Role } from "../auth/types";
import ControlPage from "../pages/ControlPage";
import HomePage from "../pages/HomePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import SettingsPage from "../pages/SettingsPage";
const StyleGuidePage = lazy(() => import("../pages/StyleGuidePage"));
const AdminApprovalsPage = lazy(() => import("../pages/AdminApprovalsPage"));
const QuoteManagementPage = lazy(() => import("../pages/QuoteManagementPage"));
const CatalogControlPage = lazy(() => import("../pages/CatalogControlPage"));
const BackendHealthPage = lazy(() => import("../pages/BackendHealthPage"));
const PlatformControlPage = lazy(() => import("../pages/PlatformControlPage"));
const ModelOpsHomePage = lazy(() => import("../features/modelops/pages/ModelOpsHomePage"));
const ModelCatalogPage = lazy(() => import("../features/modelops/pages/ModelCatalogPage"));
const CloudModelRegisterPage = lazy(() => import("../features/modelops/pages/CloudModelRegisterPage"));
const LocalModelRegisterPage = lazy(() => import("../features/modelops/pages/LocalModelRegisterPage"));
const LocalArtifactsPage = lazy(() => import("../features/modelops/pages/LocalArtifactsPage"));
const ModelAccessManagementPage = lazy(() => import("../features/modelops/pages/ModelAccessManagementPage"));
const ModelTestPage = lazy(() => import("../features/modelops/pages/ModelTestPage"));
const ModelDetailPage = lazy(() => import("../features/modelops/pages/ModelDetailPage"));
const AiPage = lazy(() => import("../pages/AiPage"));
const ChatbotPage = lazy(() => import("../pages/ChatbotPage"));
const KnowledgeChatPage = lazy(() => import("../pages/KnowledgeChatPage"));

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
    id: "control-models-test",
    path: "/control/models/:modelId/test",
    titleKey: "nav.modelTest",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    minimumRole: "admin",
    element: <ModelTestPage />,
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
