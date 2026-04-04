import type { Role } from "../../auth/types";
import {
  appRoutes,
  getBreadcrumbRoutes,
  getNavRoutes,
  getSidebarRoutes,
  isAppRouteActive,
} from "../../routes/appRoutes";
import type { ShellNavItem, TopBarPathItem, UserMenuItem } from "./types";

type Translate = (key: string) => string;

export function resolveConcreteRoutePath(routePath: string, pathname: string): string {
  if (!routePath.includes(":")) {
    return routePath;
  }

  const routeSegments = routePath.split("/").filter(Boolean);
  const pathSegments = pathname.split("/").filter(Boolean);

  return `/${routeSegments.map((segment, index) => (
    segment.startsWith(":") ? pathSegments[index] ?? segment : segment
  )).join("/")}`;
}

export function buildTopBarPathItems(pathname: string, translate: Translate): TopBarPathItem[] {
  const matchedRoutes = getBreadcrumbRoutes(pathname);
  const homeRoute = appRoutes.find((route) => route.path === "/");
  const nonHomeRoutes = matchedRoutes.filter((route) => route.path !== "/");
  const orderedRoutes = homeRoute ? [homeRoute, ...nonHomeRoutes] : nonHomeRoutes;

  return orderedRoutes.map((route, index) => ({
    id: route.id,
    label: translate(route.breadcrumbTitleKey ?? route.titleKey),
    to: resolveConcreteRoutePath(route.path, pathname),
    isCurrent: index === orderedRoutes.length - 1,
  }));
}

export function buildUserMenuItems(isAuthenticated: boolean, translate: Translate): UserMenuItem[] {
  return getNavRoutes("userMenu", { isAuthenticated }).map((route) => ({
    id: route.id,
    to: route.path,
    label: translate(route.titleKey),
  }));
}

export function buildSidebarItems(
  pathname: string,
  options: {
    isAuthenticated: boolean;
    role?: Role | null;
  },
  translate: Translate,
): ShellNavItem[] {
  return getSidebarRoutes(pathname, options).map((route) => ({
    id: route.id,
    label: translate(route.sidebar?.labelKey ?? route.titleKey),
    to: route.path,
    icon: route.sidebar?.icon ?? "home",
    isActive: isAppRouteActive(pathname, route.path),
  }));
}
