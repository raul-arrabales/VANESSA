import { activateUser, ApiError, listUsers, updateUserRole } from "../../../auth/authApi";
import { readStoredToken } from "../../../auth/storage";
import type { AuthUser, Role } from "../../../auth/types";

function requireToken(token?: string): string {
  const activeToken = token || readStoredToken();
  if (!activeToken) {
    throw new ApiError("Authentication required", 401, "missing_auth");
  }
  return activeToken;
}

export async function listPendingUsers(token?: string): Promise<AuthUser[]> {
  const result = await listUsers(requireToken(token), "pending");
  return result.users;
}

export async function activatePendingUser(userId: number, token?: string): Promise<AuthUser> {
  const result = await activateUser(userId, requireToken(token));
  return result.user;
}

export async function promotePendingUser(userId: number, role: Role, token?: string): Promise<AuthUser> {
  const result = await updateUserRole(userId, role, requireToken(token));
  return result.user;
}
