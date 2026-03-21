import type { ManagedModel } from "../../api/models";
import type { AuthUser } from "../../auth/types";

export type ModelLifecyclePermissions = {
  canRegister: boolean;
  canValidate: boolean;
  canActivate: boolean;
  canDeactivate: boolean;
  canUnregister: boolean;
  canDelete: boolean;
};

export function getModelLifecyclePermissions(
  user: AuthUser | null,
  model: ManagedModel | null,
): ModelLifecyclePermissions {
  if (!user || !model) {
    return {
      canRegister: false,
      canValidate: false,
      canActivate: false,
      canDeactivate: false,
      canUnregister: false,
      canDelete: false,
    };
  }

  if (user.role === "superadmin") {
    return {
      canRegister: true,
      canValidate: true,
      canActivate: true,
      canDeactivate: true,
      canUnregister: true,
      canDelete: true,
    };
  }

  if (user.role === "admin") {
    return {
      canRegister: false,
      canValidate: true,
      canActivate: true,
      canDeactivate: true,
      canUnregister: false,
      canDelete: false,
    };
  }

  const isOwnedByUser = model.owner_type === "user" && model.owner_user_id === user.id;
  return {
    canRegister: isOwnedByUser,
    canValidate: isOwnedByUser,
    canActivate: isOwnedByUser,
    canDeactivate: isOwnedByUser,
    canUnregister: isOwnedByUser,
    canDelete: isOwnedByUser,
  };
}
