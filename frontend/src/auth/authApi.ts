import type {
  ActivateResult,
  LoginResult,
  MeResult,
  RegisterPayload,
  RegisterResult,
  Role,
  UpdateRoleResult,
  UsersResult,
} from "./types";



type RuntimeProfile = "offline" | "online";
type RuntimeProfileSource = "database" | "default" | "forced";

type RuntimeProfileResult = {
  profile: RuntimeProfile;
  locked: boolean;
  source: RuntimeProfileSource;
};
const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

export type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: HeadersInit = {
    Accept: "application/json",
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(buildUrl(path), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const maybeJson = await response.text();
  const payload = maybeJson ? JSON.parse(maybeJson) as Record<string, unknown> : {};

  if (!response.ok) {
    const message = String(payload.message ?? payload.error ?? `HTTP ${response.status}`);
    const code = payload.error ? String(payload.error) : undefined;
    throw new ApiError(message, response.status, code);
  }

  return payload as T;
}

export function registerUser(payload: RegisterPayload, token?: string): Promise<RegisterResult> {
  return requestJson<RegisterResult>("/auth/register", { method: "POST", body: payload, token });
}

export function loginUser(identifier: string, password: string): Promise<LoginResult> {
  return requestJson<LoginResult>("/auth/login", {
    method: "POST",
    body: { identifier, password },
  });
}

export function fetchMe(token: string): Promise<MeResult> {
  return requestJson<MeResult>("/auth/me", { token });
}

export function logoutUser(token?: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>("/auth/logout", { method: "POST", token });
}

export function activateUser(userId: number, token: string): Promise<ActivateResult> {
  return requestJson<ActivateResult>(`/auth/users/${userId}/activate`, { method: "POST", token });
}

export function listUsers(token: string, status?: "pending" | "active"): Promise<UsersResult> {
  const query = status ? `?status=${status}` : "";
  return requestJson<UsersResult>(`/auth/users${query}`, { token });
}

export function updateUserRole(userId: number, role: Role, token: string): Promise<UpdateRoleResult> {
  return requestJson<UpdateRoleResult>(`/auth/users/${userId}/role`, {
    method: "PATCH",
    token,
    body: { role },
  });
}


export function fetchRuntimeProfile(token: string): Promise<RuntimeProfileResult> {
  return requestJson<RuntimeProfileResult>("/v1/runtime/profile", { token });
}

export function updateRuntimeProfile(profile: RuntimeProfile, token: string): Promise<RuntimeProfileResult> {
  return requestJson<RuntimeProfileResult>("/v1/runtime/profile", {
    method: "PUT",
    token,
    body: { profile },
  });
}
