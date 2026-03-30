import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useActionFeedback, useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { usePlatformDeploymentDetailMutations } from "./usePlatformDeploymentDetailMutations";
import { usePlatformDeploymentDetailState } from "./usePlatformDeploymentDetailState";

type UsePlatformDeploymentDetailOptions = {
  deploymentId: string;
  token: string;
};

export function usePlatformDeploymentDetail({
  deploymentId,
  token,
}: UsePlatformDeploymentDetailOptions) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const location = useLocation();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const detailState = usePlatformDeploymentDetailState({
    deploymentId,
    token,
    location,
    t,
  });

  useRouteActionFeedback(location.state);

  const mutations = usePlatformDeploymentDetailMutations({
    token,
    deployment: detailState.deployment,
    form: detailState.form,
    cloneForm: detailState.cloneForm,
    knowledgeBases: detailState.knowledgeBases,
    requiredCapabilities: detailState.requiredCapabilities,
    setLocalDeployment: detailState.setLocalDeployment,
    reload: detailState.reload,
    navigate,
    showErrorFeedback,
    showSuccessFeedback,
    t,
  });

  return {
    activationAudit: detailState.activationAudit,
    activating: mutations.activating,
    capabilities: detailState.capabilities,
    capabilityLabelByKey: detailState.capabilityLabelByKey,
    cloneForm: detailState.cloneForm,
    cloning: mutations.cloning,
    confirmDelete: mutations.confirmDelete,
    deployment: detailState.deployment,
    deploymentAudit: detailState.deploymentAudit,
    deployments: detailState.deployments,
    errorMessage: mutations.errorMessage,
    form: detailState.form,
    knowledgeBases: detailState.knowledgeBases,
    loadErrorMessage: detailState.loadErrorMessage,
    modelResourcesByCapability: detailState.modelResourcesByCapability,
    providers: detailState.providers,
    providersByCapability: detailState.providersByCapability,
    requiredCapabilities: detailState.requiredCapabilities,
    savingCapabilityKeys: mutations.savingCapabilityKeys,
    savingIdentity: mutations.savingIdentity,
    setCloneForm: detailState.setCloneForm,
    setConfirmDelete: mutations.setConfirmDelete,
    setForm: detailState.setForm,
    state: detailState.state,
    handleActivate: mutations.handleActivate,
    handleClone: mutations.handleClone,
    handleDelete: mutations.handleDelete,
    handleSaveCapability: mutations.handleSaveCapability,
    handleSaveIdentity: mutations.handleSaveIdentity,
    resetForm: detailState.resetForm,
  };
}
