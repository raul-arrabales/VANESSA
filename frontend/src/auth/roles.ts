import type { Role } from "./types";

const ROLE_WEIGHT: Record<Role, number> = {
  user: 1,
  admin: 2,
  superadmin: 3,
};

export function hasRequiredRole(current: Role, required: Role): boolean {
  return ROLE_WEIGHT[current] >= ROLE_WEIGHT[required];
}

export function getDefaultRouteForRole(_role: Role): string {
  return "/control";
}
