import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import {
  activateDeploymentProfile,
  listPlatformCapabilities,
  listPlatformDeployments,
  listPlatformProviders,
  type PlatformCapability,
  type PlatformDeploymentProfile,
  type PlatformProvider,
  type PlatformProviderValidation,
  validatePlatformProvider,
} from "../api/platform";

type LoadState = "idle" | "loading" | "success" | "error";

export default function PlatformControlPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [state, setState] = useState<LoadState>("idle");
  const [capabilities, setCapabilities] = useState<PlatformCapability[]>([]);
  const [providers, setProviders] = useState<PlatformProvider[]>([]);
  const [deployments, setDeployments] = useState<PlatformDeploymentProfile[]>([]);
  const [validatingProviderId, setValidatingProviderId] = useState("");
  const [validationResults, setValidationResults] = useState<Record<string, PlatformProviderValidation>>({});
  const [activationCandidateId, setActivationCandidateId] = useState("");
  const [activatingDeploymentId, setActivatingDeploymentId] = useState("");
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
      const [capabilitiesPayload, providersPayload, deploymentsPayload] = await Promise.all([
        listPlatformCapabilities(token),
        listPlatformProviders(token),
        listPlatformDeployments(token),
      ]);
      setCapabilities(capabilitiesPayload);
      setProviders(providersPayload);
      setDeployments(deploymentsPayload);
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
  const requiredCapabilities = capabilities.filter((capability) => capability.required);
  const coveredRequiredCapabilities = requiredCapabilities.filter((capability) => capability.active_provider !== null);

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
            <span className="field-label">{t("platformControl.summary.loadState")}</span>
            <span className="status-pill" data-state={state}>
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
                      <td><code className="code-inline">{provider.endpoint_url}</code></td>
                      <td>
                        <span className="platform-badge" data-tone={provider.enabled ? "enabled" : "disabled"}>
                          {provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled")}
                        </span>
                      </td>
                      <td>
                        {validation ? (
                          <div className="status-row">
                            <span className="platform-badge" data-tone={validation.validation.health.reachable ? "active" : "inactive"}>
                              {validation.validation.health.reachable ? t("platformControl.badges.active") : t("platformControl.badges.inactive")}
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
                          </div>
                        ) : (
                          <span className="status-text">{t("platformControl.providers.notValidated")}</span>
                        )}
                      </td>
                      <td>
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
                        <th>{t("platformControl.deployments.columns.adapter")}</th>
                        <th>{t("platformControl.deployments.columns.status")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deployment.bindings.map((binding) => (
                        <tr key={`${deployment.id}-${binding.capability}`}>
                          <td>{binding.capability}</td>
                          <td>
                            <strong>{binding.provider.display_name}</strong>
                            <div className="platform-inline-meta">
                              <code className="code-inline">{binding.provider.slug}</code>
                            </div>
                          </td>
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
                </div>
              </article>
            ))}
          </div>
        )}
      </article>

      {errorMessage && <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${errorMessage}`}</p>}
      {feedbackMessage && <p className="status-text">{feedbackMessage}</p>}
    </section>
  );
}
