import type { ManagedModel, ManagedModelLifecycleState } from "../../api/modelops/types";
import type { AuthUser } from "../../auth/types";

export const TASK_OPTIONS = [
  { value: "llm", label: "LLM / Text generation", category: "generative" as const },
  { value: "embeddings", label: "Embeddings", category: "predictive" as const },
  { value: "translation", label: "Translation", category: "generative" as const },
  { value: "classification", label: "Classification", category: "predictive" as const },
] as const;

export const MODEL_ACCESS_SCOPES = ["user", "admin", "superadmin"] as const;
export const TESTABLE_MODEL_LIFECYCLE_STATES: ManagedModelLifecycleState[] = [
  "registered",
  "validated",
  "inactive",
  "active",
];

export type TaskOption = (typeof TASK_OPTIONS)[number];

export type ModelLifecyclePermissions = {
  canRegister: boolean;
  canActivate: boolean;
  canDeactivate: boolean;
  canUnregister: boolean;
  canDelete: boolean;
};

export function isModelTestEligible(model: ManagedModel): boolean {
  return TESTABLE_MODEL_LIFECYCLE_STATES.includes(
    String(model.lifecycle_state ?? "").toLowerCase() as ManagedModelLifecycleState,
  );
}

export function getModelLifecyclePermissions(
  user: AuthUser | null,
  model: ManagedModel | null,
): ModelLifecyclePermissions {
  if (!user || !model) {
    return {
      canRegister: false,
      canActivate: false,
      canDeactivate: false,
      canUnregister: false,
      canDelete: false,
    };
  }

  if (user.role === "superadmin") {
    return {
      canRegister: true,
      canActivate: true,
      canDeactivate: true,
      canUnregister: true,
      canDelete: true,
    };
  }

  if (user.role === "admin") {
    return {
      canRegister: false,
      canActivate: true,
      canDeactivate: true,
      canUnregister: false,
      canDelete: false,
    };
  }

  const isOwnedByUser = model.owner_type === "user" && model.owner_user_id === user.id;
  return {
    canRegister: isOwnedByUser,
    canActivate: isOwnedByUser,
    canDeactivate: isOwnedByUser,
    canUnregister: isOwnedByUser,
    canDelete: isOwnedByUser,
  };
}

export function canAccessModelTesting(user: AuthUser | null): boolean {
  return user?.role === "admin" || user?.role === "superadmin";
}
