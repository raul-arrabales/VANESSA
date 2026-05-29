import { requestJson } from "./modelops/request";

export type VanessaApp = {
  id: string;
  agent_id: string;
  name: string;
  description: string;
  interface_type: "chat";
  channel_type: "vanessa_webapp";
  agent_type: "workflow" | "planner" | "react";
  published_at: string | null;
  updated_at: string | null;
};

export async function listApps(token: string): Promise<VanessaApp[]> {
  const result = await requestJson<{ apps: VanessaApp[] }>("/v1/apps", { token });
  return result.apps;
}

export async function getApp(appId: string, token: string): Promise<VanessaApp> {
  const result = await requestJson<{ app: VanessaApp }>(`/v1/apps/${encodeURIComponent(appId)}`, { token });
  return result.app;
}
