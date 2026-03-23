import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops/types";
import type { ModelLifecyclePermissions } from "../domain";

type ModelLifecycleActionsProps = {
  model: ManagedModel;
  permissions: ModelLifecyclePermissions;
  isPending: boolean;
  onRegister: () => Promise<void>;
  onActivate: () => Promise<void>;
  onDeactivate: () => Promise<void>;
  onUnregister: () => Promise<void>;
  onDelete: () => Promise<void>;
};

export default function ModelLifecycleActions({
  model,
  permissions,
  isPending,
  onRegister,
  onActivate,
  onDeactivate,
  onUnregister,
  onDelete,
}: ModelLifecycleActionsProps): JSX.Element {
  const { t } = useTranslation("common");
  const canActivateAction = permissions.canActivate && model.lifecycle_state !== "active";
  const isCurrentlyValidated =
    model.is_validation_current === true && model.last_validation_status === "success";
  const activateDisabled = isPending || !isCurrentlyValidated;

  return (
    <>
      <div className="button-row">
        {permissions.canRegister && (model.lifecycle_state === "created" || model.lifecycle_state === "unregistered") && (
          <button type="button" className="btn btn-secondary" disabled={isPending} onClick={() => void onRegister()}>
            {t("modelOps.actions.register")}
          </button>
        )}
        {canActivateAction && (
          <button type="button" className="btn btn-primary" disabled={activateDisabled} onClick={() => void onActivate()}>
            {t("modelOps.actions.activate")}
          </button>
        )}
        {permissions.canDeactivate && model.lifecycle_state === "active" && (
          <button type="button" className="btn btn-ghost" disabled={isPending} onClick={() => void onDeactivate()}>
            {t("modelOps.actions.deactivate")}
          </button>
        )}
        {permissions.canUnregister && model.lifecycle_state !== "unregistered" && (
          <button type="button" className="btn btn-ghost" disabled={isPending} onClick={() => void onUnregister()}>
            {t("modelOps.actions.unregister")}
          </button>
        )}
        {permissions.canDelete && model.lifecycle_state === "unregistered" && (
          <button type="button" className="btn btn-ghost" disabled={isPending} onClick={() => void onDelete()}>
            {t("modelOps.actions.delete")}
          </button>
        )}
      </div>
      {canActivateAction && !isCurrentlyValidated && (
        <p className="status-text">{t("modelOps.detail.activationRequiresValidation")}</p>
      )}
    </>
  );
}
