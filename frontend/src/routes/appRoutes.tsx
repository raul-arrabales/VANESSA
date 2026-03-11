import type { JSX } from "react";
import type { Role } from "../auth/types";
import AiPage from "../pages/AiPage";
import AdminApprovalsPage from "../pages/AdminApprovalsPage";
import BackendHealthPage from "../pages/BackendHealthPage";
import ChatbotPage from "../pages/ChatbotPage";
import ControlModelsPage from "../pages/ControlModelsPage";
import ControlPage from "../pages/ControlPage";
import HomePage from "../pages/HomePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import SettingsPage from "../pages/SettingsPage";
import StyleGuidePage from "../pages/StyleGuidePage";

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
    id: "control-models",
    path: "/control/models",
    titleKey: "nav.models",
    section: "control",
    showInNav: false,
    showInBreadcrumbs: true,
    requiresAuth: true,
    element: <ControlModelsPage />,
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
