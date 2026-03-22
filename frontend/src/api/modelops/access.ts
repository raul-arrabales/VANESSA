import { ApiError } from "../../auth/authApi";
import { requestJson } from "./request";
import type { ModelScopeAssignment } from "./types";

export async function listModelAssignments(token: string): Promise<ModelScopeAssignment[]> {
  try {
    const result = await requestJson<{ assignments: ModelScopeAssignment[] }>("/v1/modelops/sharing", { token });
    return result.assignments;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return [];
    }
    throw error;
  }
}

export async function updateModelAssignment(
  scope: string,
  modelIds: string[],
  token: string,
): Promise<ModelScopeAssignment> {
  const result = await requestJson<{ assignment: ModelScopeAssignment }>("/v1/modelops/sharing", {
    method: "PUT",
    token,
    body: { scope, model_ids: modelIds },
  });

  return result.assignment;
}
