import { ApiError } from "../auth/authApi";

export type RuntimeProfile = "offline" | "online";
export type RuntimeProfileSource = "database" | "default" | "forced";

export type RuntimeProfileResult = {
  profile: RuntimeProfile;
  locked: boolean;
  source: RuntimeProfileSource;
};

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

async function requestRuntimeProfile(path: string, token: string, profile?: RuntimeProfile): Promise<RuntimeProfileResult> {
  const response = await fetch(buildUrl(path), {
    method: profile ? "PUT" : "GET",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: profile ? JSON.stringify({ profile }) : undefined,
  });

  const maybeJson = await response.text();
  const payload = maybeJson ? JSON.parse(maybeJson) as Record<string, unknown> : {};

  if (!response.ok) {
    const message = String(payload.message ?? payload.error ?? `HTTP ${response.status}`);
    const code = payload.error ? String(payload.error) : undefined;
    throw new ApiError(message, response.status, code);
  }

  return payload as RuntimeProfileResult;
}

export function getRuntimeProfile(token: string): Promise<RuntimeProfileResult> {
  return requestRuntimeProfile("/v1/runtime/profile", token);
}

export function setRuntimeProfile(token: string, profile: RuntimeProfile): Promise<RuntimeProfileResult> {
  return requestRuntimeProfile("/v1/runtime/profile", token, profile);
}
