import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  assignPlatformProviderLoadedModel,
  clearPlatformProviderLoadedModel,
  deletePlatformProvider,
  updatePlatformProvider,
  validatePlatformProvider,
  type PlatformProviderValidation,
} from "../api/platform";
import { listModelOpsModels } from "../api/modelops/models";
import type { ManagedModel } from "../api/modelops/types";
import { useAuth } from "../auth/AuthProvider";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import PlatformProviderForm from "../features/platform-control/components/PlatformProviderForm";
import PlatformProviderUsagePanel from "../features/platform-control/components/PlatformProviderUsagePanel";
import PlatformProviderValidationPanel from "../features/platform-control/components/PlatformProviderValidationPanel";
import { usePlatformProvidersData } from "../features/platform-control/hooks/usePlatformProvidersData";
import {
  buildProviderForm,
  getActiveDeployment,
  parseJsonObject,
  type ProviderFormState,
} from "../features/platform-control/utils";

function readLocationFeedback(state: unknown): string {
  if (state && typeof state === "object" && "feedbackMessage" in state && typeof state.feedbackMessage === "string") {
    return state.feedbackMessage;
  }
  return "";
}

type ProviderLoadPanelPhase = "idle" | "loading" | "reconciling" | "loaded" | "error";

type StoredProviderLoadStatus = {
  providerId: string;
  requestedModelId: string;
  requestedModelName: string;
  statusOpen: boolean;
  dismissedTerminalState: boolean;
};

const PROVIDER_LOAD_STATUS_STORAGE_PREFIX = "vanessa:platform-provider-load:";

function normalizeProviderLoadPhase(value: string | null | undefined): ProviderLoadPanelPhase {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (
    normalized === "loading"
    || normalized === "reconciling"
    || normalized === "loaded"
    || normalized === "error"
  ) {
    return normalized;
  }
  return "idle";
}

function isActiveProviderLoadPhase(phase: ProviderLoadPanelPhase): boolean {
  return phase === "loading" || phase === "reconciling";
}

function isTerminalProviderLoadPhase(phase: ProviderLoadPanelPhase): boolean {
  return phase === "loaded" || phase === "error";
}

function providerLoadStatusStorageKey(providerId: string): string {
  return `${PROVIDER_LOAD_STATUS_STORAGE_PREFIX}${providerId}`;
}

function readStoredProviderLoadStatus(providerId: string): StoredProviderLoadStatus | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const rawValue = window.sessionStorage.getItem(providerLoadStatusStorageKey(providerId));
    if (!rawValue) {
      return null;
    }
    const parsed = JSON.parse(rawValue) as Partial<StoredProviderLoadStatus>;
    if (parsed.providerId !== providerId) {
      return null;
    }
    return {
      providerId,
      requestedModelId: String(parsed.requestedModelId ?? ""),
      requestedModelName: String(parsed.requestedModelName ?? ""),
      statusOpen: Boolean(parsed.statusOpen),
      dismissedTerminalState: Boolean(parsed.dismissedTerminalState),
    };
  } catch {
    return null;
  }
}

function writeStoredProviderLoadStatus(payload: StoredProviderLoadStatus): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(
    providerLoadStatusStorageKey(payload.providerId),
    JSON.stringify(payload),
  );
}

function clearStoredProviderLoadStatus(providerId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(providerLoadStatusStorageKey(providerId));
}

function sameStoredProviderLoadStatus(
  left: StoredProviderLoadStatus | null,
  right: StoredProviderLoadStatus | null,
): boolean {
  if (left === right) {
    return true;
  }
  if (!left || !right) {
    return false;
  }
  return (
    left.providerId === right.providerId
    && left.requestedModelId === right.requestedModelId
    && left.requestedModelName === right.requestedModelName
    && left.statusOpen === right.statusOpen
    && left.dismissedTerminalState === right.dismissedTerminalState
  );
}

export default function PlatformProviderDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { providerId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { state, errorMessage: loadErrorMessage, capabilities, providers, providerFamilies, deployments, reload } = usePlatformProvidersData(token);
  const [form, setForm] = useState<ProviderFormState | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<PlatformProviderValidation | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [slotModels, setSlotModels] = useState<ManagedModel[]>([]);
  const [slotModelId, setSlotModelId] = useState("");
  const [slotLoading, setSlotLoading] = useState(false);
  const [isLoadPanelOpen, setIsLoadPanelOpen] = useState(false);
  const [loadPanelPhase, setLoadPanelPhase] = useState<ProviderLoadPanelPhase>("idle");
  const [trackedLoad, setTrackedLoad] = useState<StoredProviderLoadStatus | null>(null);

  const provider = providers.find((item) => item.id === providerId) ?? null;
  const providerFamily = provider ? providerFamilies.find((family) => family.provider_key === provider.provider_key) ?? null : null;
  const activeDeployment = getActiveDeployment(deployments);
  const isUsedByActiveDeployment = useMemo(() => (
    deployments.some(
      (deployment) =>
        deployment.is_active && deployment.bindings.some((binding) => binding.provider.id === providerId),
    )
  ), [deployments, providerId]);
  const supportsLocalSlot = provider
    ? (provider.capability === "llm_inference" || provider.capability === "embeddings")
      && provider.provider_key !== "openai_compatible_cloud_llm"
      && provider.provider_key !== "openai_compatible_cloud_embeddings"
    : false;
  const selectedSlotModel = useMemo(
    () => slotModels.find((model) => model.id === slotModelId) ?? null,
    [slotModelId, slotModels],
  );

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

  useEffect(() => {
    if (!supportsLocalSlot || !provider) {
      return;
    }
    if (provider.load_state !== "loading" && provider.load_state !== "reconciling") {
      return;
    }
    const timer = window.setTimeout(() => {
      void reload();
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [provider, reload, supportsLocalSlot]);

  useEffect(() => {
    if (!supportsLocalSlot || !providerId) {
      setTrackedLoad(null);
      setIsLoadPanelOpen(false);
      setLoadPanelPhase("idle");
      return;
    }
    setTrackedLoad(readStoredProviderLoadStatus(providerId));
  }, [providerId, supportsLocalSlot]);

  useEffect(() => {
    if (!supportsLocalSlot || !provider) {
      return;
    }

    const backendPhase = normalizeProviderLoadPhase(provider.load_state);
    const providerModelId = provider.loaded_managed_model_id ?? "";
    const providerModelName = provider.loaded_managed_model_name ?? providerModelId;
    let nextTrackedLoad = trackedLoad;

    if (isActiveProviderLoadPhase(backendPhase)) {
      const candidate: StoredProviderLoadStatus = {
        providerId: provider.id,
        requestedModelId: providerModelId || trackedLoad?.requestedModelId || slotModelId,
        requestedModelName: providerModelName || trackedLoad?.requestedModelName || selectedSlotModel?.name || slotModelId,
        statusOpen: true,
        dismissedTerminalState: false,
      };
      if (!sameStoredProviderLoadStatus(trackedLoad, candidate)) {
        setTrackedLoad(candidate);
        writeStoredProviderLoadStatus(candidate);
        nextTrackedLoad = candidate;
      }
      setLoadPanelPhase(backendPhase);
      setIsLoadPanelOpen(true);
      return;
    }

    if (isTerminalProviderLoadPhase(backendPhase)) {
      setLoadPanelPhase(backendPhase);
      if (nextTrackedLoad && nextTrackedLoad.statusOpen && !nextTrackedLoad.dismissedTerminalState) {
        const candidate: StoredProviderLoadStatus = {
          ...nextTrackedLoad,
          requestedModelId: nextTrackedLoad.requestedModelId || providerModelId,
          requestedModelName: nextTrackedLoad.requestedModelName || providerModelName,
        };
        if (!sameStoredProviderLoadStatus(nextTrackedLoad, candidate)) {
          setTrackedLoad(candidate);
          writeStoredProviderLoadStatus(candidate);
        }
        setIsLoadPanelOpen(true);
      }
      return;
    }

    if (!nextTrackedLoad || nextTrackedLoad.dismissedTerminalState || !nextTrackedLoad.statusOpen) {
      setIsLoadPanelOpen(false);
      setLoadPanelPhase("idle");
    }
  }, [provider, selectedSlotModel, slotModelId, supportsLocalSlot, trackedLoad]);

  function persistTrackedLoad(nextTrackedLoad: StoredProviderLoadStatus): void {
    setTrackedLoad(nextTrackedLoad);
    writeStoredProviderLoadStatus(nextTrackedLoad);
  }

  function dismissTrackedLoadPanel(): void {
    if (!provider || !trackedLoad) {
      setIsLoadPanelOpen(false);
      return;
    }
    const dismissedStatus: StoredProviderLoadStatus = {
      ...trackedLoad,
      statusOpen: false,
      dismissedTerminalState: true,
    };
    persistTrackedLoad(dismissedStatus);
    setIsLoadPanelOpen(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !provider || !form) {
      return;
    }

    setSaving(true);
    setErrorMessage("");
    setFeedbackMessage("");
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
      setFeedbackMessage(t("platformControl.feedback.providerUpdated", { name: form.displayName }));
      await reload();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.providerSaveFailed"));
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
    setFeedbackMessage("");
    try {
      const nextValidation = await validatePlatformProvider(provider.id, token);
      setValidation(nextValidation);
      setFeedbackMessage(t("platformControl.feedback.validationSuccess", { slug: provider.slug }));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.validationFailed"));
    } finally {
      setValidating(false);
    }
  }

  async function handleDelete(): Promise<void> {
    if (!token || !provider) {
      return;
    }

    setErrorMessage("");
    setFeedbackMessage("");
    try {
      await deletePlatformProvider(provider.id, token);
      navigate("/control/platform/providers", {
        state: { feedbackMessage: t("platformControl.feedback.providerDeleted") },
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.providerDeleteFailed"));
    }
  }

  async function handleAssignLoadedModel(): Promise<void> {
    if (!token || !provider || !slotModelId) {
      return;
    }
    setErrorMessage("");
    setFeedbackMessage("");
    const nextTrackedLoad: StoredProviderLoadStatus = {
      providerId: provider.id,
      requestedModelId: slotModelId,
      requestedModelName: selectedSlotModel?.name ?? slotModelId,
      statusOpen: true,
      dismissedTerminalState: false,
    };
    persistTrackedLoad(nextTrackedLoad);
    setLoadPanelPhase("loading");
    setIsLoadPanelOpen(true);
    try {
      const updatedProvider = await assignPlatformProviderLoadedModel(provider.id, slotModelId, token);
      setSlotModelId(updatedProvider.loaded_managed_model_id ?? slotModelId);
      setLoadPanelPhase(normalizeProviderLoadPhase(updatedProvider.load_state) || "loading");
      await reload();
    } catch (error) {
      clearStoredProviderLoadStatus(provider.id);
      setTrackedLoad(null);
      setIsLoadPanelOpen(false);
      setLoadPanelPhase("idle");
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.providerLoadedModelAssignFailed"));
    }
  }

  async function handleClearLoadedModel(): Promise<void> {
    if (!token || !provider) {
      return;
    }
    setErrorMessage("");
    setFeedbackMessage("");
    try {
      const updatedProvider = await clearPlatformProviderLoadedModel(provider.id, token);
      setSlotModelId(updatedProvider.loaded_managed_model_id ?? "");
      clearStoredProviderLoadStatus(provider.id);
      setTrackedLoad(null);
      setIsLoadPanelOpen(false);
      setLoadPanelPhase("idle");
      setFeedbackMessage(t("platformControl.feedback.providerLoadedModelCleared", { name: updatedProvider.display_name }));
      await reload();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.providerLoadedModelClearFailed"));
    }
  }

  const combinedFeedback = feedbackMessage || readLocationFeedback(location.state);
  const loadedModelPrimary = provider?.loaded_managed_model_name
    ?? provider?.loaded_managed_model_id
    ?? provider?.loaded_runtime_model_id
    ?? provider?.loaded_local_path
    ?? t("platformControl.summary.none");
  const loadedModelSecondaryDetailCandidate = provider?.loaded_runtime_model_id ?? provider?.loaded_local_path ?? null;
  const loadedModelSecondaryDetail = loadedModelSecondaryDetailCandidate && loadedModelSecondaryDetailCandidate !== loadedModelPrimary
    ? loadedModelSecondaryDetailCandidate
    : null;
  const providerLoadState = String(provider?.load_state ?? "empty").trim() || "empty";
  const loadStateHelperText = provider?.load_error
    ? provider.load_error
    : providerLoadState === "loaded"
      ? t("platformControl.providers.loadedModelStateHintLoaded")
      : providerLoadState === "reconciling"
        ? t("platformControl.providers.loadedModelStateHintReconciling")
        : providerLoadState === "loading"
          ? t("platformControl.providers.loadedModelStateHintLoading")
          : t("platformControl.providers.loadedModelStateHintEmpty");
  const loadPanelModelName = trackedLoad?.requestedModelName || provider?.loaded_managed_model_name || provider?.loaded_managed_model_id || t("platformControl.summary.none");
  const loadPanelModelId = trackedLoad?.requestedModelId || provider?.loaded_managed_model_id || t("platformControl.summary.none");
  const loadPanelRuntimeLabel = provider?.loaded_runtime_model_id ?? provider?.loaded_local_path ?? providerLoadState;
  const loadPanelPhaseLabel = t(`platformControl.providers.loadPanelPhases.${loadPanelPhase}`);
  const loadPanelSummary = loadPanelPhase === "loading"
    ? t("platformControl.providers.loadPanelSummaryLoading", { name: loadPanelModelName })
    : loadPanelPhase === "reconciling"
      ? t("platformControl.providers.loadPanelSummaryReconciling", { name: loadPanelModelName })
      : loadPanelPhase === "loaded"
        ? t("platformControl.providers.loadPanelSummaryLoaded", { name: loadPanelModelName })
        : loadPanelPhase === "error"
          ? t("platformControl.providers.loadPanelSummaryError", { name: loadPanelModelName })
          : "";
  const loadTimelineItems = [
    {
      label: t("platformControl.providers.loadPanelTimelineAccepted"),
      state: "done",
    },
    {
      label: t("platformControl.providers.loadPanelTimelineLoading"),
      state: loadPanelPhase === "loaded"
        ? "done"
        : loadPanelPhase === "error"
          ? "error"
          : isActiveProviderLoadPhase(loadPanelPhase)
            ? "active"
            : "pending",
    },
    {
      label: loadPanelPhase === "error"
        ? t("platformControl.providers.loadPanelTimelineFailed")
        : t("platformControl.providers.loadPanelTimelineReady"),
      state: loadPanelPhase === "loaded"
        ? "done"
        : loadPanelPhase === "error"
          ? "error"
          : "pending",
    },
  ];

  return (
    <PlatformPageLayout
      title={provider?.display_name ?? t("platformControl.providers.detailTitle")}
      description={provider ? t("platformControl.providers.detailDescription") : t("platformControl.providers.notFound")}
      errorMessage={errorMessage || loadErrorMessage}
      feedbackMessage={combinedFeedback}
      actions={(
        <Link className="btn btn-secondary" to="/control/platform/providers">
          {t("platformControl.actions.viewProviders")}
        </Link>
      )}
    >
      {state === "success" && !provider ? (
        <article className="panel card-stack">
          <p className="status-text">{t("platformControl.providers.notFound")}</p>
        </article>
      ) : null}

      {provider ? (
        <>
          <article className="panel card-stack">
            <div className="platform-card-header">
              <div className="status-row">
                <h3 className="section-title">{provider.display_name}</h3>
                <span className="status-text">
                  <code className="code-inline">{provider.slug}</code>
                </span>
              </div>
              <div className="platform-inline-meta">
                <span className="platform-badge" data-tone={provider.enabled ? "enabled" : "disabled"}>
                  {provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled")}
                </span>
                {isUsedByActiveDeployment ? (
                  <span className="platform-badge" data-tone="active">
                    {t("platformControl.badges.activeDeployment")}
                  </span>
                ) : null}
              </div>
            </div>
            <p className="status-text">{provider.description || t("platformControl.providers.noDescription")}</p>
            <div className="platform-detail-grid">
              <div className="platform-summary-card">
                <span className="field-label">{t("platformControl.providers.familyLabel")}</span>
                <strong>{providerFamily?.display_name ?? provider.provider_key}</strong>
                <span className="status-text">{provider.provider_key}</span>
              </div>
              <div className="platform-summary-card">
                <span className="field-label">{t("platformControl.providers.capabilityLabel")}</span>
                <strong>{provider.capability}</strong>
                <span className="status-text">{provider.adapter_kind}</span>
              </div>
              <div className="platform-summary-card">
                <span className="field-label">{t("platformControl.providers.endpointLabel")}</span>
                <strong>{provider.endpoint_url}</strong>
                <span className="status-text">{provider.healthcheck_url ?? t("platformControl.summary.none")}</span>
              </div>
              <div className="platform-summary-card">
                <span className="field-label">{t("platformControl.providers.activeDeploymentLabel")}</span>
                <strong>{activeDeployment?.display_name ?? t("platformControl.summary.none")}</strong>
                <span className="status-text">{isUsedByActiveDeployment ? t("platformControl.providers.activeReference") : t("platformControl.providers.inactiveReference")}</span>
              </div>
            </div>
          </article>

          <PlatformProviderValidationPanel
            validation={validation}
            isValidating={validating}
            onValidate={() => void handleValidate()}
          />

          {supportsLocalSlot ? (
            <article className="panel card-stack">
              <div className="status-row">
                <h3 className="section-title">{t("platformControl.providers.loadedModelTitle")}</h3>
                <p className="status-text">{t("platformControl.providers.loadedModelDescription")}</p>
              </div>
              <div className="platform-detail-grid">
                <div className="platform-summary-card">
                  <span className="field-label">{t("platformControl.providers.loadedModelLabel")}</span>
                  <strong>{loadedModelPrimary}</strong>
                  {loadedModelSecondaryDetail ? (
                    <span className="status-text">{loadedModelSecondaryDetail}</span>
                  ) : null}
                </div>
                <div className="platform-summary-card">
                  <span className="field-label">{t("platformControl.providers.loadedModelStateLabel")}</span>
                  <strong>{providerLoadState}</strong>
                  <span className={provider?.load_error ? "status-text error-text" : "status-text"}>{loadStateHelperText}</span>
                </div>
              </div>
              <label className="field-label" htmlFor="provider-loaded-model">
                {t("platformControl.providers.loadedModelSelectLabel")}
              </label>
              <select
                id="provider-loaded-model"
                className="field-input"
                value={slotModelId}
                disabled={slotLoading}
                onChange={(event) => setSlotModelId(event.currentTarget.value)}
              >
                <option value="">{t("platformControl.providers.loadedModelPlaceholder")}</option>
                {slotModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.id})
                  </option>
                ))}
              </select>
              <p className="status-text">{t("platformControl.providers.loadedModelHelp")}</p>
              <div className="button-row">
                <button type="button" className="btn btn-primary" disabled={!slotModelId} onClick={() => void handleAssignLoadedModel()}>
                  {t("platformControl.actions.assignLoadedModel")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => void handleClearLoadedModel()}>
                  {t("platformControl.actions.clearLoadedModel")}
                </button>
              </div>
            </article>
          ) : null}

          <PlatformProviderUsagePanel
            providerId={provider.id}
            capabilities={capabilities}
            deployments={deployments}
          />

          {form ? (
            <article className="panel card-stack">
              <div className="status-row">
                <h3 className="section-title">{t("platformControl.sections.settings")}</h3>
                <p className="status-text">{t("platformControl.providers.settingsDescription")}</p>
              </div>
              <PlatformProviderForm
                value={form}
                providerFamilies={providerFamilies}
                familyDisabled
                helperText={t("platformControl.providers.editing", { slug: provider.slug })}
                isSubmitting={saving}
                submitLabel={t("platformControl.actions.saveProvider")}
                submitBusyLabel={t("platformControl.actions.saving")}
                secondaryAction={{
                  label: t("platformControl.actions.reset"),
                  onClick: () => setForm(buildProviderForm(provider)),
                }}
                onChange={setForm}
                onSubmit={(event) => void handleSubmit(event)}
              />
            </article>
          ) : null}

          <article className="panel card-stack">
            <div className="status-row">
              <h3 className="section-title">{t("platformControl.sections.danger")}</h3>
              <p className="status-text">{t("platformControl.providers.deleteDescription")}</p>
            </div>
            <div className="platform-inline-meta">
              {confirmDelete ? (
                <>
                  <button type="button" className="btn btn-secondary" onClick={() => setConfirmDelete(false)}>
                    {t("platformControl.actions.cancel")}
                  </button>
                  <button type="button" className="btn btn-primary" onClick={() => void handleDelete()}>
                    {t("platformControl.actions.confirmDelete")}
                  </button>
                </>
              ) : (
                <button type="button" className="btn btn-secondary" onClick={() => setConfirmDelete(true)}>
                  {t("platformControl.actions.delete")}
                </button>
              )}
            </div>
          </article>
        </>
      ) : null}

      {provider && supportsLocalSlot && isLoadPanelOpen && loadPanelPhase !== "idle" ? (
        <aside
          className="provider-load-panel panel"
          role="status"
          aria-live="polite"
          aria-label={t("platformControl.providers.loadPanelTitle")}
        >
          <div className="provider-load-panel-header">
            <div className="card-stack">
              <p className="eyebrow">{t("platformControl.providers.loadPanelTitle")}</p>
              <h3 className="section-title">{provider.display_name}</h3>
            </div>
            <span className="status-pill" data-state={loadPanelPhase === "loaded" ? "success" : loadPanelPhase === "error" ? "error" : "loading"}>
              {loadPanelPhaseLabel}
            </span>
          </div>
          <p className="modal-message">{loadPanelSummary}</p>
          <div className="platform-detail-grid">
            <div className="platform-summary-card">
              <span className="field-label">{t("platformControl.providers.loadPanelRequestedModelLabel")}</span>
              <strong>{loadPanelModelName}</strong>
              <span className="status-text">{loadPanelModelId}</span>
            </div>
            <div className="platform-summary-card">
              <span className="field-label">{t("platformControl.providers.loadPanelRuntimeLabel")}</span>
              <strong>{loadPanelRuntimeLabel}</strong>
              <span className={provider.load_error ? "status-text error-text" : "status-text"}>
                {loadStateHelperText}
              </span>
            </div>
          </div>
          <div
            className="provider-load-progress"
            data-phase={loadPanelPhase}
            role="progressbar"
            aria-valuetext={loadPanelPhaseLabel}
          >
            <div className="provider-load-progress-bar" />
          </div>
          <ul className="provider-load-timeline">
            {loadTimelineItems.map((item) => (
              <li key={item.label} className="provider-load-timeline-item" data-state={item.state}>
                <span className="provider-load-timeline-marker" aria-hidden="true" />
                <span className="status-text">{item.label}</span>
              </li>
            ))}
          </ul>
          {isTerminalProviderLoadPhase(loadPanelPhase) ? (
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={dismissTrackedLoadPanel}>
                {t("platformControl.providers.loadPanelDismiss")}
              </button>
            </div>
          ) : null}
        </aside>
      ) : null}
    </PlatformPageLayout>
  );
}
