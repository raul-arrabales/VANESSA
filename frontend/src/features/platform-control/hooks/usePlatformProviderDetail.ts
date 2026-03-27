import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  assignPlatformProviderLoadedModel,
  clearPlatformProviderLoadedModel,
  deletePlatformProvider,
  updatePlatformProvider,
  validatePlatformProvider,
  type PlatformProviderValidation,
} from "../../../api/platform";
import { listModelOpsModels } from "../../../api/modelops/models";
import type { ManagedModel } from "../../../api/modelops/types";
import { useActionFeedback, useRouteActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import { getActiveDeployment } from "../platformTopology";
import { buildProviderForm, parseJsonObject, type ProviderFormState } from "../providerForm";
import { buildProviderLoadDisplayData, type StoredProviderLoadStatus } from "../providerLoad";
import { usePlatformProviderLoadState } from "./usePlatformProviderLoadState";
import { usePlatformProvidersData } from "./usePlatformProvidersData";

type UsePlatformProviderDetailOptions = {
  providerId: string;
  token: string;
};

export function usePlatformProviderDetail({
  providerId,
  token,
}: UsePlatformProviderDetailOptions) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const location = useLocation();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const {
    state,
    errorMessage: loadErrorMessage,
    capabilities,
    providers,
    providerFamilies,
    deployments,
    reload,
  } = usePlatformProvidersData(token);
  const [form, setForm] = useState<ProviderFormState | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<PlatformProviderValidation | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [slotModels, setSlotModels] = useState<ManagedModel[]>([]);
  const [slotModelId, setSlotModelId] = useState("");
  const [slotLoading, setSlotLoading] = useState(false);

  const provider = providers.find((item) => item.id === providerId) ?? null;
  const providerFamily = provider
    ? providerFamilies.find((family) => family.provider_key === provider.provider_key) ?? null
    : null;
  const activeDeployment = getActiveDeployment(deployments);
  const isUsedByActiveDeployment = useMemo(
    () => deployments.some(
      (deployment) =>
        deployment.is_active && deployment.bindings.some((binding) => binding.provider.id === providerId),
    ),
    [deployments, providerId],
  );
  const supportsLocalSlot = provider
    ? (provider.capability === "llm_inference" || provider.capability === "embeddings")
      && provider.provider_key !== "openai_compatible_cloud_llm"
      && provider.provider_key !== "openai_compatible_cloud_embeddings"
    : false;
  const selectedSlotModel = useMemo(
    () => slotModels.find((model) => model.id === slotModelId) ?? null,
    [slotModelId, slotModels],
  );
  const {
    isLoadPanelOpen,
    loadPanelPhase,
    trackedLoad,
    persistTrackedLoad,
    dismissTrackedLoadPanel,
    resetTrackedLoadState,
  } = usePlatformProviderLoadState({
    provider,
    providerId,
    supportsLocalSlot,
    slotModelId,
    selectedSlotModel,
    reload,
  });
  const loadDisplay = useMemo(
    () => buildProviderLoadDisplayData(provider, trackedLoad, loadPanelPhase, t),
    [loadPanelPhase, provider, t, trackedLoad],
  );

  useRouteActionFeedback(location.state);

  useEffect(() => {
    if (provider) {
      setForm(buildProviderForm(provider));
      setSlotModelId(provider.loaded_managed_model_id ?? "");
    }
  }, [provider]);

  useEffect(() => {
    if (!token || !provider || !supportsLocalSlot) {
      setSlotModels([]);
      setSlotLoading(false);
      return;
    }
    let isActive = true;
    setSlotLoading(true);
    void listModelOpsModels(token, { capability: provider.capability })
      .then((models) => {
        if (!isActive) {
          return;
        }
        setSlotModels(models.filter((model) => model.backend === "local"));
      })
      .catch(() => {
        if (isActive) {
          setSlotModels([]);
        }
      })
      .finally(() => {
        if (isActive) {
          setSlotLoading(false);
        }
      });
    return () => {
      isActive = false;
    };
  }, [provider, supportsLocalSlot, token]);

  async function handleSubmit(): Promise<void> {
    if (!token || !provider || !form) {
      return;
    }

    setSaving(true);
    setErrorMessage("");
    try {
      const config = parseJsonObject(
        form.configText,
        t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.config") }),
      );
      const secretRefs = parseJsonObject(
        form.secretRefsText,
        t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.secretRefs") }),
      ) as Record<string, string>;
      await updatePlatformProvider(
        provider.id,
        {
          slug: form.slug,
          display_name: form.displayName,
          description: form.description,
          endpoint_url: form.endpointUrl,
          healthcheck_url: form.healthcheckUrl || null,
          enabled: form.enabled,
          config,
          secret_refs: secretRefs,
        },
        token,
      );
      showSuccessFeedback(t("platformControl.feedback.providerUpdated", { name: form.displayName }));
      await reload();
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.providerSaveFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate(): Promise<void> {
    if (!token || !provider) {
      return;
    }

    setValidating(true);
    setErrorMessage("");
    try {
      const nextValidation = await validatePlatformProvider(provider.id, token);
      setValidation(nextValidation);
      showSuccessFeedback(t("platformControl.feedback.validationSuccess", { slug: provider.slug }));
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.validationFailed"));
    } finally {
      setValidating(false);
    }
  }

  async function handleDelete(): Promise<void> {
    if (!token || !provider) {
      return;
    }

    setErrorMessage("");
    try {
      await deletePlatformProvider(provider.id, token);
      navigate("/control/platform/providers", {
        state: withActionFeedbackState({
          kind: "success",
          message: t("platformControl.feedback.providerDeleted"),
        }),
      });
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.providerDeleteFailed"));
    }
  }

  async function handleAssignLoadedModel(): Promise<void> {
    if (!token || !provider || !slotModelId) {
      return;
    }
    setErrorMessage("");
    const nextTrackedLoad: StoredProviderLoadStatus = {
      providerId: provider.id,
      requestedModelId: slotModelId,
      requestedModelName: selectedSlotModel?.name ?? slotModelId,
      statusOpen: true,
      dismissedTerminalState: false,
    };
    persistTrackedLoad(nextTrackedLoad);
    try {
      const updatedProvider = await assignPlatformProviderLoadedModel(provider.id, slotModelId, token);
      setSlotModelId(updatedProvider.loaded_managed_model_id ?? slotModelId);
      showSuccessFeedback(t("platformControl.feedback.providerLoadedModelAssigned", { name: updatedProvider.display_name }));
      await reload();
    } catch (error) {
      resetTrackedLoadState();
      showErrorFeedback(error, t("platformControl.feedback.providerLoadedModelAssignFailed"));
    }
  }

  async function handleClearLoadedModel(): Promise<void> {
    if (!token || !provider) {
      return;
    }
    setErrorMessage("");
    try {
      const updatedProvider = await clearPlatformProviderLoadedModel(provider.id, token);
      setSlotModelId(updatedProvider.loaded_managed_model_id ?? "");
      resetTrackedLoadState();
      showSuccessFeedback(t("platformControl.feedback.providerLoadedModelCleared", { name: updatedProvider.display_name }));
      await reload();
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.providerLoadedModelClearFailed"));
    }
  }

  return {
    activeDeployment,
    capabilities,
    confirmDelete,
    deployments,
    dismissTrackedLoadPanel,
    errorMessage,
    form,
    isLoadPanelOpen,
    isUsedByActiveDeployment,
    loadDisplay,
    loadErrorMessage,
    loadPanelPhase,
    provider,
    providerFamily,
    providers,
    providerFamilies,
    resetProviderForm: () => provider ? setForm(buildProviderForm(provider)) : undefined,
    saving,
    setConfirmDelete,
    setForm,
    setSlotModelId,
    slotLoading,
    slotModelId,
    slotModels,
    state,
    supportsLocalSlot,
    validating,
    validation,
    handleAssignLoadedModel,
    handleClearLoadedModel,
    handleDelete,
    handleSubmit,
    handleValidate,
  };
}
