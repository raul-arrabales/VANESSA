import { requestJson } from "./request";
import type { ModelCredential } from "./types";

export async function listModelCredentials(token: string): Promise<ModelCredential[]> {
  const result = await requestJson<{ credentials: ModelCredential[] }>("/v1/modelops/credentials", { token });
  return result.credentials;
}

export async function createModelCredential(
  payload: {
    provider: string;
    display_name?: string;
    api_base_url?: string;
    api_key: string;
    credential_scope?: "platform" | "personal";
    owner_user_id?: number;
  },
  token: string,
): Promise<ModelCredential> {
  const result = await requestJson<{ credential: ModelCredential }>("/v1/modelops/credentials", {
    method: "POST",
    token,
    body: payload,
  });
  return result.credential;
}

export async function revokeModelCredential(credentialId: string, token: string): Promise<ModelCredential> {
  const result = await requestJson<{ credential: ModelCredential }>(`/v1/modelops/credentials/${encodeURIComponent(credentialId)}/revoke`, {
    method: "POST",
    token,
  });
  return result.credential;
}
