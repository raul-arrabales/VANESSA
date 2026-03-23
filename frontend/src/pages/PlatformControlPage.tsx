import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import { listModelOpsModels, type ManagedModel } from "../api/modelops";
import {
  activateDeploymentProfile,
  cloneDeploymentProfile,
  createDeploymentProfile,
  createPlatformProvider,
  deleteDeploymentProfile,
  deletePlatformProvider,
  listPlatformActivationAudit,
  listPlatformCapabilities,
  listPlatformDeployments,
  listPlatformProviderFamilies,
  listPlatformProviders,
  type PlatformActivationAuditEntry,
  type PlatformCapability,
  type PlatformDeploymentProfile,
  type PlatformProvider,
  type PlatformProviderFamily,
  type PlatformProviderValidation,
  updateDeploymentProfile,
  updatePlatformProvider,
  validatePlatformProvider,
} from "../api/platform";

type LoadState = "idle" | "loading" | "success" | "error";
type ProviderFormMode = "create" | "edit";
type DeploymentFormMode = "create" | "edit" | "clone";

type ProviderFormState = {
  mode: ProviderFormMode;
  providerId: string;
  providerKey: string;
  slug: string;
  displayName: string;
  description: string;
  endpointUrl: string;
  healthcheckUrl: string;
  enabled: boolean;
  configText: string;
  secretRefsText: string;
};

type DeploymentFormState = {
  mode: DeploymentFormMode;
  deploymentId: string;
  sourceDeploymentId: string;
  slug: string;
  displayName: string;
  description: string;
  providerIdsByCapability: Record<string, string>;
  servedModelIdsByCapability: Record<string, string[]>;
  defaultServedModelIdsByCapability: Record<string, string>;
};

const DEFAULT_PROVIDER_FORM: ProviderFormState = {
  mode: "create",
  providerId: "",
  providerKey: "",
  slug: "",
  displayName: "",
  description: "",
  endpointUrl: "",
  healthcheckUrl: "",
  enabled: true,
  configText: "{}",
  secretRefsText: "{}",
};

const DEFAULT_DEPLOYMENT_FORM: DeploymentFormState = {
  mode: "create",
  deploymentId: "",
  sourceDeploymentId: "",
  slug: "",
  displayName: "",
  description: "",
  providerIdsByCapability: {},
  servedModelIdsByCapability: {},
  defaultServedModelIdsByCapability: {},
};

function stringifyJson(value: Record<string, unknown> | Record<string, string>): string {
  return JSON.stringify(value, null, 2);
}

function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  const normalized = text.trim();
  if (!normalized) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error(errorMessage);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(errorMessage);
  }

  return parsed as Record<string, unknown>;
}

function buildProviderForm(provider: PlatformProvider): ProviderFormState {
  return {
    mode: "edit",
    providerId: provider.id,
    providerKey: provider.provider_key,
    slug: provider.slug,
    displayName: provider.display_name,
    description: provider.description,
    endpointUrl: provider.endpoint_url,
    healthcheckUrl: provider.healthcheck_url ?? "",
    enabled: provider.enabled,
    configText: stringifyJson(provider.config),
    secretRefsText: stringifyJson(provider.secret_refs),
  };
}

function buildDeploymentForm(
  deployment: PlatformDeploymentProfile,
  options: { mode: DeploymentFormMode },
): DeploymentFormState {
  const { mode } = options;
  const suffix = mode === "clone" ? "-copy" : "";
  const nameSuffix = mode === "clone" ? " Copy" : "";

  return {
    mode,
    deploymentId: mode === "edit" ? deployment.id : "",
    sourceDeploymentId: mode === "clone" ? deployment.id : "",
    slug: mode === "clone" ? `${deployment.slug}${suffix}` : deployment.slug,
    displayName: mode === "clone" ? `${deployment.display_name}${nameSuffix}` : deployment.display_name,
    description: deployment.description,
    providerIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, binding.provider.id]),
    ),
    servedModelIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, (binding.served_models ?? []).map((model) => model.id)]),
    ),
    defaultServedModelIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, binding.default_served_model_id ?? ""]),
    ),
  };
}

function capabilityRequiresServedModel(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings";
}

function summarizeBindingServedModels(binding: PlatformDeploymentProfile["bindings"][number], noneLabel: string): string {
  const defaultModel = binding.default_served_model;
  if (!defaultModel) {
    return noneLabel;
  }
  const defaultLabel = defaultModel.name ?? defaultModel.id;
  const additionalCount = Math.max((binding.served_models ?? []).length - 1, 0);
  if (additionalCount === 0) {
    return defaultLabel;
  }
  return `${defaultLabel} (+${additionalCount})`;
}

export default function PlatformControlPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [state, setState] = useState<LoadState>("idle");
  const [capabilities, setCapabilities] = useState<PlatformCapability[]>([]);
  const [providerFamilies, setProviderFamilies] = useState<PlatformProviderFamily[]>([]);
  const [providers, setProviders] = useState<PlatformProvider[]>([]);
  const [deployments, setDeployments] = useState<PlatformDeploymentProfile[]>([]);
  const [eligibleModelsByCapability, setEligibleModelsByCapability] = useState<Record<string, ManagedModel[]>>({});
  const [activationAudit, setActivationAudit] = useState<PlatformActivationAuditEntry[]>([]);
  const [validatingProviderId, setValidatingProviderId] = useState("");
  const [validationResults, setValidationResults] = useState<Record<string, PlatformProviderValidation>>({});
  const [providerForm, setProviderForm] = useState<ProviderFormState>(DEFAULT_PROVIDER_FORM);
  const [deploymentForm, setDeploymentForm] = useState<DeploymentFormState>(DEFAULT_DEPLOYMENT_FORM);
  const [activationCandidateId, setActivationCandidateId] = useState("");
  const [providerDeleteCandidateId, setProviderDeleteCandidateId] = useState("");
  const [deploymentDeleteCandidateId, setDeploymentDeleteCandidateId] = useState("");
  const [savingProvider, setSavingProvider] = useState(false);
  const [savingDeployment, setSavingDeployment] = useState(false);
  const [activatingDeploymentId, setActivatingDeploymentId] = useState("");
  const [deletingProviderId, setDeletingProviderId] = useState("");
  const [deletingDeploymentId, setDeletingDeploymentId] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState("");

  async function loadPlatformState(): Promise<void> {
    if (!token) {
      setState("error");
      setErrorMessage(t("platformControl.feedback.authRequired"));
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [
        capabilitiesPayload,
        providerFamiliesPayload,
        providersPayload,
        deploymentsPayload,
        activationAuditPayload,
        llmModelsPayload,
        embeddingsModelsPayload,
      ] =
        await Promise.all([
          listPlatformCapabilities(token),
          listPlatformProviderFamilies(token),
          listPlatformProviders(token),
          listPlatformDeployments(token),
          listPlatformActivationAudit(token),
          listModelOpsModels(token, { eligible: true, capability: "llm_inference" }),
          listModelOpsModels(token, { eligible: true, capability: "embeddings" }),
        ]);
      setCapabilities(capabilitiesPayload);
      setProviderFamilies(providerFamiliesPayload);
      setProviders(providersPayload);
      setDeployments(deploymentsPayload);
      setEligibleModelsByCapability({
        llm_inference: llmModelsPayload,
        embeddings: embeddingsModelsPayload,
      });
      setActivationAudit(activationAuditPayload);
      setState("success");
    } catch (error) {
      setState("error");
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.loadFailed"));
    }
  }

  useEffect(() => {
    void loadPlatformState();
  }, [token]);

  const activeDeployment = deployments.find((deployment) => deployment.is_active) ?? null;
  const latestActivation = activationAudit[0] ?? null;
  const requiredCapabilities = capabilities.filter((capability) => capability.required);
  const coveredRequiredCapabilities = requiredCapabilities.filter((capability) => capability.active_provider !== null);
  const capabilityLabelByKey = new Map(capabilities.map((capability) => [capability.capability, capability.display_name]));
  const providersByCapability = requiredCapabilities.reduce<Record<string, PlatformProvider[]>>((accumulator, capability) => {
    accumulator[capability.capability] = providers.filter((provider) => provider.capability === capability.capability);
    return accumulator;
  }, {});
  const servedModelsByCapability = requiredCapabilities.reduce<Record<string, ManagedModel[]>>((accumulator, capability) => {
    if (!capabilityRequiresServedModel(capability.capability)) {
      accumulator[capability.capability] = [];
      return accumulator;
    }
    accumulator[capability.capability] = eligibleModelsByCapability[capability.capability] ?? [];
    return accumulator;
  }, {});

  function updateServedModelsForCapability(capability: string, servedModelIds: string[]): void {
    setDeploymentForm((current) => {
      const previousDefault = current.defaultServedModelIdsByCapability[capability] ?? "";
      const nextDefault = servedModelIds.includes(previousDefault) ? previousDefault : (servedModelIds[0] ?? "");
      return {
        ...current,
        servedModelIdsByCapability: {
          ...current.servedModelIdsByCapability,
          [capability]: servedModelIds,
        },
        defaultServedModelIdsByCapability: {
          ...current.defaultServedModelIdsByCapability,
          [capability]: nextDefault,
        },
      };
    });
  }

  async function handleValidateProvider(providerId: string): Promise<void> {
    if (!token) {
      return;
    }

    setValidatingProviderId(providerId);
    setFeedbackMessage("");
    setErrorMessage("");
    try {
      const result = await validatePlatformProvider(providerId, token);
      setValidationResults((current) => ({ ...current, [providerId]: result }));
      setFeedbackMessage(t("platformControl.feedback.validationSuccess", { slug: result.provider.slug }));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.validationFailed"));
    } finally {
      setValidatingProviderId("");
    }
  }

  async function handleProviderSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }

    setSavingProvider(true);
    setFeedbackMessage("");
    setErrorMessage("");
    try {
      const config = parseJsonObject(
        providerForm.configText,
        t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.config") }),
      );
      const secretRefs = parseJsonObject(
        providerForm.secretRefsText,
        t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.secretRefs") }),
      ) as Record<string, string>;
      if (providerForm.mode === "create") {
        await createPlatformProvider(
          {
            provider_key: providerForm.providerKey,
            slug: providerForm.slug,
            display_name: providerForm.displayName,
            description: providerForm.description,
            endpoint_url: providerForm.endpointUrl,
            healthcheck_url: providerForm.healthcheckUrl || null,
            enabled: providerForm.enabled,
            config,
            secret_refs: secretRefs,
          },
          token,
        );
        setFeedbackMessage(t("platformControl.feedback.providerCreated", { name: providerForm.displayName }));
      } else {
        await updatePlatformProvider(
          providerForm.providerId,
          {
            slug: providerForm.slug,
            display_name: providerForm.displayName,
            description: providerForm.description,
            endpoint_url: providerForm.endpointUrl,
            healthcheck_url: providerForm.healthcheckUrl || null,
            enabled: providerForm.enabled,
            config,
            secret_refs: secretRefs,
          },
          token,
        );
        setFeedbackMessage(t("platformControl.feedback.providerUpdated", { name: providerForm.displayName }));
      }
      setProviderForm(DEFAULT_PROVIDER_FORM);
      await loadPlatformState();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.providerSaveFailed"));
    } finally {
      setSavingProvider(false);
    }
  }

  async function handleDeleteProvider(providerId: string): Promise<void> {
    if (!token) {
      return;
    }

    setDeletingProviderId(providerId);
    setFeedbackMessage("");
    setErrorMessage("");
    try {
      await deletePlatformProvider(providerId, token);
      setProviderDeleteCandidateId("");
      if (providerForm.providerId === providerId) {
        setProviderForm(DEFAULT_PROVIDER_FORM);
      }
      setFeedbackMessage(t("platformControl.feedback.providerDeleted"));
      await loadPlatformState();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.providerDeleteFailed"));
    } finally {
      setDeletingProviderId("");
    }
  }

  async function handleDeploymentSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    if (deploymentForm.mode !== "clone") {
      const missingBinding = requiredCapabilities.find(
        (capability) => !deploymentForm.providerIdsByCapability[capability.capability],
      );
      if (missingBinding) {
        setErrorMessage(t("platformControl.feedback.bindingRequired"));
        return;
      }
      const missingServedModel = requiredCapabilities.find(
        (capability) =>
          capabilityRequiresServedModel(capability.capability) &&
          (deploymentForm.servedModelIdsByCapability[capability.capability]?.length ?? 0) === 0,
      );
      if (missingServedModel) {
        setErrorMessage(
          t("platformControl.feedback.servedModelRequired", {
            capability: missingServedModel.display_name,
          }),
        );
        return;
      }
      const missingDefaultServedModel = requiredCapabilities.find(
        (capability) =>
          capabilityRequiresServedModel(capability.capability) &&
          (deploymentForm.servedModelIdsByCapability[capability.capability]?.length ?? 0) > 0 &&
          !deploymentForm.defaultServedModelIdsByCapability[capability.capability],
      );
      if (missingDefaultServedModel) {
        setErrorMessage(
          t("platformControl.feedback.defaultServedModelRequired", {
            capability: missingDefaultServedModel.display_name,
          }),
        );
        return;
      }
    }

    setSavingDeployment(true);
    setFeedbackMessage("");
    setErrorMessage("");
    try {
      if (deploymentForm.mode === "clone") {
        await cloneDeploymentProfile(
          deploymentForm.sourceDeploymentId,
          {
            slug: deploymentForm.slug,
            display_name: deploymentForm.displayName,
            description: deploymentForm.description,
          },
          token,
        );
        setFeedbackMessage(t("platformControl.feedback.deploymentCloned", { name: deploymentForm.displayName }));
      } else {
        const payload = {
          slug: deploymentForm.slug,
          display_name: deploymentForm.displayName,
          description: deploymentForm.description,
          bindings: requiredCapabilities.map((capability) => ({
            capability: capability.capability,
            provider_id: deploymentForm.providerIdsByCapability[capability.capability],
            served_model_ids: capabilityRequiresServedModel(capability.capability)
              ? deploymentForm.servedModelIdsByCapability[capability.capability] ?? []
              : [],
            default_served_model_id: capabilityRequiresServedModel(capability.capability)
              ? deploymentForm.defaultServedModelIdsByCapability[capability.capability] || null
              : null,
            config: {},
          })),
        };
        if (deploymentForm.mode === "create") {
          await createDeploymentProfile(payload, token);
          setFeedbackMessage(t("platformControl.feedback.deploymentCreated", { name: deploymentForm.displayName }));
        } else {
          await updateDeploymentProfile(deploymentForm.deploymentId, payload, token);
          setFeedbackMessage(t("platformControl.feedback.deploymentUpdated", { name: deploymentForm.displayName }));
        }
      }
      setDeploymentForm(DEFAULT_DEPLOYMENT_FORM);
      await loadPlatformState();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSavingDeployment(false);
    }
  }

  async function handleActivateDeployment(deploymentId: string): Promise<void> {
    if (!token) {
      return;
    }

    setActivatingDeploymentId(deploymentId);
    setFeedbackMessage("");
    setErrorMessage("");
    try {
      const activated = await activateDeploymentProfile(deploymentId, token);
      setActivationCandidateId("");
      setFeedbackMessage(t("platformControl.feedback.activationSuccess", { name: activated.display_name }));
      await loadPlatformState();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.activationFailed"));
    } finally {
      setActivatingDeploymentId("");
    }
  }

  async function handleDeleteDeployment(deploymentId: string): Promise<void> {
    if (!token) {
      return;
    }

    setDeletingDeploymentId(deploymentId);
    setFeedbackMessage("");
    setErrorMessage("");
    try {
      await deleteDeploymentProfile(deploymentId, token);
      setDeploymentDeleteCandidateId("");
      if (deploymentForm.deploymentId === deploymentId || deploymentForm.sourceDeploymentId === deploymentId) {
        setDeploymentForm(DEFAULT_DEPLOYMENT_FORM);
      }
      setFeedbackMessage(t("platformControl.feedback.deploymentDeleted"));
      await loadPlatformState();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.deploymentDeleteFailed"));
    } finally {
      setDeletingDeploymentId("");
    }
  }

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <div className="status-row">
          <p className="eyebrow">{t("platformControl.eyebrow")}</p>
          <h2 className="section-title">{t("platformControl.title")}</h2>
          <p className="status-text">{t("platformControl.description")}</p>
        </div>
        <div className="platform-summary-grid">
          <div className="platform-summary-card">
            <span className="field-label">{t("platformControl.summary.activeDeployment")}</span>
            <strong>{activeDeployment?.display_name ?? t("platformControl.summary.none")}</strong>
            <span className="status-text">{activeDeployment?.slug ?? t("platformControl.summary.none")}</span>
          </div>
          <div className="platform-summary-card">
            <span className="field-label">{t("platformControl.summary.requiredCoverage")}</span>
            <strong>{`${coveredRequiredCapabilities.length}/${requiredCapabilities.length}`}</strong>
            <span className="status-text">{t("platformControl.summary.requiredCoverageDescription")}</span>
          </div>
          <div className="platform-summary-card">
            <span className="field-label">{t("platformControl.summary.lastActivation")}</span>
            <strong>{latestActivation?.deployment_profile.display_name ?? t("platformControl.summary.none")}</strong>
            <span className="status-text">{latestActivation?.activated_at ?? t("platformControl.summary.none")}</span>
          </div>
          <div className="platform-summary-card">
            <span className="field-label">{t("platformControl.summary.loadState")}</span>
            <span className="platform-badge" data-tone={state === "success" ? "active" : state === "error" ? "inactive" : "required"}>
              {t(`platformControl.state.${state}`)}
            </span>
          </div>
        </div>
      </article>

      <article className="panel card-stack">
        <div className="platform-section-header">
          <div className="status-row">
            <h3 className="section-title">{t("platformControl.sections.capabilities")}</h3>
            <p className="status-text">{t("platformControl.capabilities.description")}</p>
          </div>
          <button type="button" className="btn btn-primary" onClick={() => void loadPlatformState()} disabled={state === "loading"}>
            {state === "loading" ? t("platformControl.actions.refreshing") : t("platformControl.actions.refresh")}
          </button>
        </div>

        {capabilities.length === 0 ? (
          <p className="status-text">{t("platformControl.capabilities.empty")}</p>
        ) : (
          <div className="platform-capability-grid">
            {capabilities.map((capability) => (
              <article key={capability.capability} className="platform-capability-card">
                <div className="platform-card-header">
                  <h4 className="section-title">{capability.display_name}</h4>
                  {capability.required && (
                    <span className="platform-badge" data-tone="required">
                      {t("platformControl.badges.required")}
                    </span>
                  )}
                </div>
                <p className="status-text">{capability.description}</p>
                {capability.active_provider ? (
                  <div className="status-row">
                    <span className="field-label">{t("platformControl.capabilities.activeProvider")}</span>
                    <strong>{capability.active_provider.display_name}</strong>
                    <span className="status-text">
                      <code className="code-inline">{capability.active_provider.slug}</code>
                    </span>
                  </div>
                ) : (
                  <p className="status-text">{t("platformControl.capabilities.unbound")}</p>
                )}
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.sections.providers")}</h3>
          <p className="status-text">{t("platformControl.providers.description")}</p>
        </div>

        <form className="card-stack" onSubmit={(event) => void handleProviderSubmit(event)}>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.family")}</span>
              <select
                className="field-input"
                value={providerForm.providerKey}
                disabled={providerForm.mode === "edit"}
                onChange={(event) => setProviderForm((current) => ({ ...current, providerKey: event.target.value }))}
              >
                <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                {providerFamilies.map((family) => (
                  <option key={family.provider_key} value={family.provider_key}>
                    {family.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.slug")}</span>
              <input
                className="field-input"
                value={providerForm.slug}
                onChange={(event) => setProviderForm((current) => ({ ...current, slug: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.displayName")}</span>
              <input
                className="field-input"
                value={providerForm.displayName}
                onChange={(event) => setProviderForm((current) => ({ ...current, displayName: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.endpoint")}</span>
              <input
                className="field-input"
                value={providerForm.endpointUrl}
                onChange={(event) => setProviderForm((current) => ({ ...current, endpointUrl: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.healthcheck")}</span>
              <input
                className="field-input"
                value={providerForm.healthcheckUrl}
                onChange={(event) => setProviderForm((current) => ({ ...current, healthcheckUrl: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.enabled")}</span>
              <select
                className="field-input"
                value={providerForm.enabled ? "true" : "false"}
                onChange={(event) =>
                  setProviderForm((current) => ({ ...current, enabled: event.target.value === "true" }))
                }
              >
                <option value="true">{t("platformControl.badges.enabled")}</option>
                <option value="false">{t("platformControl.badges.disabled")}</option>
              </select>
            </label>
          </div>
          <label className="card-stack">
            <span className="field-label">{t("platformControl.forms.provider.description")}</span>
            <textarea
              className="field-input quote-admin-textarea"
              value={providerForm.description}
              onChange={(event) => setProviderForm((current) => ({ ...current, description: event.target.value }))}
            />
          </label>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.config")}</span>
              <textarea
                className="field-input quote-admin-textarea"
                value={providerForm.configText}
                onChange={(event) => setProviderForm((current) => ({ ...current, configText: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.provider.secretRefs")}</span>
              <textarea
                className="field-input quote-admin-textarea"
                value={providerForm.secretRefsText}
                onChange={(event) => setProviderForm((current) => ({ ...current, secretRefsText: event.target.value }))}
              />
            </label>
          </div>
          <div className="platform-action-row">
            <span className="status-text">
              {providerForm.mode === "create"
                ? t("platformControl.providers.createHelp")
                : t("platformControl.providers.editing", { slug: providerForm.slug })}
            </span>
            <div className="form-actions">
              {providerForm.mode === "edit" && (
                <button type="button" className="btn btn-secondary" onClick={() => setProviderForm(DEFAULT_PROVIDER_FORM)}>
                  {t("platformControl.actions.reset")}
                </button>
              )}
              <button type="submit" className="btn btn-primary" disabled={savingProvider}>
                {savingProvider
                  ? t("platformControl.actions.saving")
                  : providerForm.mode === "create"
                    ? t("platformControl.actions.createProvider")
                    : t("platformControl.actions.saveProvider")}
              </button>
            </div>
          </div>
        </form>

        {providers.length === 0 ? (
          <p className="status-text">{t("platformControl.providers.empty")}</p>
        ) : (
          <div className="health-table-wrap">
            <table className="health-table" aria-label={t("platformControl.providers.tableAria")}>
              <thead>
                <tr>
                  <th>{t("platformControl.providers.columns.provider")}</th>
                  <th>{t("platformControl.providers.columns.capability")}</th>
                  <th>{t("platformControl.providers.columns.endpoint")}</th>
                  <th>{t("platformControl.providers.columns.status")}</th>
                  <th>{t("platformControl.providers.columns.validation")}</th>
                  <th>{t("platformControl.providers.columns.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((provider) => {
                  const validation = validationResults[provider.id];
                  return (
                    <tr key={provider.id}>
                      <td>
                        <strong>{provider.display_name}</strong>
                        <div className="platform-inline-meta">
                          <code className="code-inline">{provider.slug}</code>
                          <code className="code-inline">{provider.provider_key}</code>
                        </div>
                      </td>
                      <td>{provider.capability}</td>
                      <td>
                        <code className="code-inline">{provider.endpoint_url}</code>
                      </td>
                      <td>
                        <span className="platform-badge" data-tone={provider.enabled ? "enabled" : "disabled"}>
                          {provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled")}
                        </span>
                      </td>
                      <td>
                        {validation ? (
                          <div className="status-row">
                            <span className="platform-badge" data-tone={validation.validation.health.reachable ? "active" : "inactive"}>
                              {validation.validation.health.reachable
                                ? t("platformControl.badges.active")
                                : t("platformControl.badges.inactive")}
                            </span>
                            <span className="status-text">
                              {t("platformControl.providers.validationStatus", { code: validation.validation.health.status_code })}
                            </span>
                            {typeof validation.validation.models_reachable === "boolean" && (
                              <span className="status-text">
                                {validation.validation.models_reachable
                                  ? t("platformControl.providers.modelsReachable")
                                  : t("platformControl.providers.modelsUnavailable")}
                              </span>
                            )}
                            {typeof validation.validation.embeddings_reachable === "boolean" && (
                              <span className="status-text">
                                {validation.validation.embeddings_reachable
                                  ? t("platformControl.providers.embeddingsReachable", {
                                      dimension: validation.validation.embedding_dimension ?? 0,
                                    })
                                  : t("platformControl.providers.embeddingsUnavailable")}
                              </span>
                            )}
                            {validation.validation.binding_error && (
                              <span className="status-text">
                                {t(`platformControl.providers.bindingErrors.${validation.validation.binding_error}`)}
                              </span>
                            )}
                            {(validation.validation.served_model_errors ?? []).map((error, index) => (
                              <span key={`${provider.id}-${error.code}-${error.served_model_id ?? index}`} className="status-text">
                                {t(`platformControl.providers.bindingErrors.${error.code}`, {
                                  modelId: error.served_model_id ?? t("platformControl.summary.none"),
                                  runtimeModelId: error.runtime_model_id ?? t("platformControl.summary.none"),
                                })}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="status-text">{t("platformControl.providers.notValidated")}</span>
                        )}
                      </td>
                      <td>
                        <div className="platform-inline-meta">
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => void handleValidateProvider(provider.id)}
                            disabled={validatingProviderId === provider.id}
                          >
                            {validatingProviderId === provider.id
                              ? t("platformControl.actions.validating")
                              : t("platformControl.actions.validate")}
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setProviderForm(buildProviderForm(provider))}
                          >
                            {t("platformControl.actions.edit")}
                          </button>
                          {providerDeleteCandidateId === provider.id ? (
                            <>
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => setProviderDeleteCandidateId("")}
                                disabled={deletingProviderId === provider.id}
                              >
                                {t("platformControl.actions.cancel")}
                              </button>
                              <button
                                type="button"
                                className="btn btn-primary"
                                onClick={() => void handleDeleteProvider(provider.id)}
                                disabled={deletingProviderId === provider.id}
                              >
                                {deletingProviderId === provider.id
                                  ? t("platformControl.actions.deleting")
                                  : t("platformControl.actions.confirmDelete")}
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              className="btn btn-secondary"
                              onClick={() => setProviderDeleteCandidateId(provider.id)}
                            >
                              {t("platformControl.actions.delete")}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.sections.deployments")}</h3>
          <p className="status-text">{t("platformControl.deployments.description")}</p>
        </div>

        <form className="card-stack" onSubmit={(event) => void handleDeploymentSubmit(event)}>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
              <input
                className="field-input"
                value={deploymentForm.slug}
                onChange={(event) => setDeploymentForm((current) => ({ ...current, slug: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
              <input
                className="field-input"
                value={deploymentForm.displayName}
                onChange={(event) => setDeploymentForm((current) => ({ ...current, displayName: event.target.value }))}
              />
            </label>
            {requiredCapabilities.map((capability) => (
              <div key={capability.capability} className="card-stack">
                <label className="card-stack">
                  <span className="field-label">
                    {t("platformControl.forms.deployment.providerForCapability", {
                      capability: capability.display_name,
                    })}
                  </span>
                  <select
                    className="field-input"
                    value={deploymentForm.providerIdsByCapability[capability.capability] ?? ""}
                    disabled={deploymentForm.mode === "clone"}
                    onChange={(event) =>
                      setDeploymentForm((current) => ({
                        ...current,
                        providerIdsByCapability: {
                          ...current.providerIdsByCapability,
                          [capability.capability]: event.target.value,
                        },
                      }))
                    }
                  >
                    <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                    {(providersByCapability[capability.capability] ?? []).map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                {capabilityRequiresServedModel(capability.capability) && (
                  <>
                    <label className="card-stack">
                      <span className="field-label">
                        {t("platformControl.forms.deployment.servedModelsForCapability", {
                          capability: capability.display_name,
                        })}
                      </span>
                      <select
                        className="field-input"
                        multiple
                        value={deploymentForm.servedModelIdsByCapability[capability.capability] ?? []}
                        disabled={deploymentForm.mode === "clone"}
                        onChange={(event) =>
                          updateServedModelsForCapability(
                            capability.capability,
                            Array.from(event.target.selectedOptions, (option) => option.value),
                          )
                        }
                      >
                        {(servedModelsByCapability[capability.capability] ?? []).map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="card-stack">
                      <span className="field-label">
                        {t("platformControl.forms.deployment.defaultServedModelForCapability", {
                          capability: capability.display_name,
                        })}
                      </span>
                      <select
                        className="field-input"
                        value={deploymentForm.defaultServedModelIdsByCapability[capability.capability] ?? ""}
                        disabled={deploymentForm.mode === "clone"}
                        onChange={(event) =>
                          setDeploymentForm((current) => ({
                            ...current,
                            defaultServedModelIdsByCapability: {
                              ...current.defaultServedModelIdsByCapability,
                              [capability.capability]: event.target.value,
                            },
                          }))
                        }
                      >
                        <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                        {(servedModelsByCapability[capability.capability] ?? [])
                          .filter((model) =>
                            (deploymentForm.servedModelIdsByCapability[capability.capability] ?? []).includes(model.id),
                          )
                          .map((model) => (
                            <option key={model.id} value={model.id}>
                              {model.name}
                            </option>
                          ))}
                      </select>
                    </label>
                  </>
                )}
              </div>
            ))}
          </div>
          <label className="card-stack">
            <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
            <textarea
              className="field-input quote-admin-textarea"
              value={deploymentForm.description}
              onChange={(event) => setDeploymentForm((current) => ({ ...current, description: event.target.value }))}
            />
          </label>
          <div className="platform-action-row">
            <span className="status-text">
              {deploymentForm.mode === "create"
                ? t("platformControl.deployments.createHelp")
                : deploymentForm.mode === "edit"
                  ? t("platformControl.deployments.editing", { slug: deploymentForm.slug })
                  : t("platformControl.deployments.cloning", { slug: deploymentForm.slug })}
            </span>
            <div className="form-actions">
              {deploymentForm.mode !== "create" && (
                <button type="button" className="btn btn-secondary" onClick={() => setDeploymentForm(DEFAULT_DEPLOYMENT_FORM)}>
                  {t("platformControl.actions.reset")}
                </button>
              )}
              <button type="submit" className="btn btn-primary" disabled={savingDeployment}>
                {savingDeployment
                  ? t("platformControl.actions.saving")
                  : deploymentForm.mode === "create"
                    ? t("platformControl.actions.createDeployment")
                    : deploymentForm.mode === "edit"
                      ? t("platformControl.actions.saveDeployment")
                      : t("platformControl.actions.cloneDeployment")}
              </button>
            </div>
          </div>
        </form>

        {deployments.length === 0 ? (
          <p className="status-text">{t("platformControl.deployments.empty")}</p>
        ) : (
          <div className="platform-deployment-list">
            {deployments.map((deployment) => (
              <article key={deployment.id} className="platform-deployment-card">
                <div className="platform-card-header">
                  <div className="status-row">
                    <h4 className="section-title">{deployment.display_name}</h4>
                    <span className="status-text">
                      <code className="code-inline">{deployment.slug}</code>
                    </span>
                  </div>
                  <span className="platform-badge" data-tone={deployment.is_active ? "active" : "inactive"}>
                    {deployment.is_active ? t("platformControl.badges.active") : t("platformControl.badges.inactive")}
                  </span>
                </div>
                <p className="status-text">{deployment.description || t("platformControl.deployments.noDescription")}</p>
                <div className="health-table-wrap">
                  <table className="health-table" aria-label={t("platformControl.deployments.tableAria", { name: deployment.display_name })}>
                    <thead>
                      <tr>
                        <th>{t("platformControl.deployments.columns.capability")}</th>
                        <th>{t("platformControl.deployments.columns.provider")}</th>
                        <th>{t("platformControl.deployments.columns.servedModel")}</th>
                        <th>{t("platformControl.deployments.columns.adapter")}</th>
                        <th>{t("platformControl.deployments.columns.status")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deployment.bindings.map((binding) => (
                        <tr key={`${deployment.id}-${binding.capability}`}>
                          <td>{capabilityLabelByKey.get(binding.capability) ?? binding.capability}</td>
                          <td>
                            <strong>{binding.provider.display_name}</strong>
                            <div className="platform-inline-meta">
                              <code className="code-inline">{binding.provider.slug}</code>
                            </div>
                          </td>
                          <td>{summarizeBindingServedModels(binding, t("platformControl.summary.none"))}</td>
                          <td>{binding.provider.adapter_kind}</td>
                          <td>
                            <span className="platform-badge" data-tone={binding.provider.enabled ? "enabled" : "disabled"}>
                              {binding.provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled")}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="platform-action-row">
                  <div className="platform-inline-meta">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setDeploymentForm(buildDeploymentForm(deployment, { mode: "edit" }))}
                    >
                      {t("platformControl.actions.edit")}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setDeploymentForm(buildDeploymentForm(deployment, { mode: "clone" }))}
                    >
                      {t("platformControl.actions.clone")}
                    </button>
                  </div>
                  <div className="platform-inline-meta">
                    {activationCandidateId === deployment.id && !deployment.is_active ? (
                      <>
                        <span className="status-text">{t("platformControl.deployments.confirmActivation")}</span>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => setActivationCandidateId("")}
                          disabled={activatingDeploymentId === deployment.id}
                        >
                          {t("platformControl.actions.cancel")}
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => void handleActivateDeployment(deployment.id)}
                          disabled={activatingDeploymentId === deployment.id}
                        >
                          {activatingDeploymentId === deployment.id
                            ? t("platformControl.actions.activating")
                            : t("platformControl.actions.confirmActivate")}
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => setActivationCandidateId(deployment.id)}
                        disabled={deployment.is_active}
                      >
                        {deployment.is_active ? t("platformControl.actions.active") : t("platformControl.actions.activate")}
                      </button>
                    )}

                    {deploymentDeleteCandidateId === deployment.id ? (
                      <>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => setDeploymentDeleteCandidateId("")}
                          disabled={deletingDeploymentId === deployment.id}
                        >
                          {t("platformControl.actions.cancel")}
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => void handleDeleteDeployment(deployment.id)}
                          disabled={deletingDeploymentId === deployment.id || deployment.is_active}
                        >
                          {deletingDeploymentId === deployment.id
                            ? t("platformControl.actions.deleting")
                            : t("platformControl.actions.confirmDelete")}
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setDeploymentDeleteCandidateId(deployment.id)}
                        disabled={deployment.is_active}
                      >
                        {t("platformControl.actions.delete")}
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.sections.audit")}</h3>
          <p className="status-text">{t("platformControl.audit.description")}</p>
        </div>
        {activationAudit.length === 0 ? (
          <p className="status-text">{t("platformControl.audit.empty")}</p>
        ) : (
          <div className="health-table-wrap">
            <table className="health-table" aria-label={t("platformControl.audit.tableAria")}>
              <thead>
                <tr>
                  <th>{t("platformControl.audit.columns.activatedAt")}</th>
                  <th>{t("platformControl.audit.columns.deployment")}</th>
                  <th>{t("platformControl.audit.columns.previousDeployment")}</th>
                  <th>{t("platformControl.audit.columns.actor")}</th>
                </tr>
              </thead>
              <tbody>
                {activationAudit.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.activated_at}</td>
                    <td>{entry.deployment_profile.display_name}</td>
                    <td>{entry.previous_deployment_profile?.display_name ?? t("platformControl.summary.none")}</td>
                    <td>{entry.activated_by_user_id ?? t("platformControl.summary.none")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      {errorMessage && <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${errorMessage}`}</p>}
      {feedbackMessage && <p className="status-text">{feedbackMessage}</p>}
    </section>
  );
}
