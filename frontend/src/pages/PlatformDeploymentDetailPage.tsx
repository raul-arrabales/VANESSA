import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  activateDeploymentProfile,
  cloneDeploymentProfile,
  deleteDeploymentProfile,
  updateDeploymentProfile,
} from "../api/platform";
import { useAuth } from "../auth/AuthProvider";
import PlatformDeploymentAuditTable from "../features/platform-control/components/PlatformDeploymentAuditTable";
import PlatformDeploymentForm from "../features/platform-control/components/PlatformDeploymentForm";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import { usePlatformDeploymentEditorData } from "../features/platform-control/hooks/usePlatformDeploymentEditorData";
import {
  buildCloneForm,
  buildDeploymentForm,
  buildDeploymentMutationInput,
  getCapabilityProviders,
  getManagedModelsByCapability,
  summarizeBindingResources,
  validateDeploymentForm,
  type DeploymentCloneFormState,
  type DeploymentFormState,
} from "../features/platform-control/utils";

function readLocationFeedback(state: unknown): string {
  if (state && typeof state === "object" && "feedbackMessage" in state && typeof state.feedbackMessage === "string") {
    return state.feedbackMessage;
  }
  return "";
}

export default function PlatformDeploymentDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { deploymentId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    state,
    errorMessage: loadErrorMessage,
    capabilities,
    providers,
    deployments,
    activationAudit,
    eligibleModelsByCapability,
    reload,
  } = usePlatformDeploymentEditorData(token);
  const [form, setForm] = useState<DeploymentFormState | null>(null);
  const [cloneForm, setCloneForm] = useState<DeploymentCloneFormState | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [activating, setActivating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const deployment = deployments.find((item) => item.id === deploymentId) ?? null;
  const requiredCapabilities = useMemo(
    () => capabilities.filter((capability) => capability.required),
    [capabilities],
  );
  const capabilityLabelByKey = useMemo(
    () => new Map(capabilities.map((capability) => [capability.capability, capability.display_name])),
    [capabilities],
  );
  const providersByCapability = useMemo(
    () => getCapabilityProviders(providers, requiredCapabilities),
    [providers, requiredCapabilities],
  );
  const modelResourcesByCapability = useMemo(
    () => getManagedModelsByCapability(eligibleModelsByCapability, requiredCapabilities),
    [eligibleModelsByCapability, requiredCapabilities],
  );
  const deploymentAudit = activationAudit.filter((entry) => entry.deployment_profile.id === deploymentId);

  useEffect(() => {
    if (deployment) {
      setForm(buildDeploymentForm(deployment));
      setCloneForm(buildCloneForm(deployment));
    }
  }, [deployment]);

  async function handleSave(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !deployment || !form) {
      return;
    }

    const validationError = validateDeploymentForm(requiredCapabilities, form, {
      bindingRequiredMessage: t("platformControl.feedback.bindingRequired"),
      resourceRequiredMessage: (capabilityDisplayName) =>
        t("platformControl.feedback.resourceRequired", { capability: capabilityDisplayName }),
      defaultResourceRequiredMessage: (capabilityDisplayName) =>
        t("platformControl.feedback.defaultResourceRequired", { capability: capabilityDisplayName }),
    });
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setSaving(true);
    setErrorMessage("");
    setFeedbackMessage("");
    try {
      await updateDeploymentProfile(
        deployment.id,
        buildDeploymentMutationInput(requiredCapabilities, form),
        token,
      );
      setFeedbackMessage(t("platformControl.feedback.deploymentUpdated", { name: form.displayName }));
      await reload();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function handleClone(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !deployment || !cloneForm) {
      return;
    }

    setCloning(true);
    setErrorMessage("");
    setFeedbackMessage("");
    try {
      const cloned = await cloneDeploymentProfile(
        deployment.id,
        {
          slug: cloneForm.slug,
          display_name: cloneForm.displayName,
          description: cloneForm.description,
        },
        token,
      );
      navigate(`/control/platform/deployments/${cloned.id}`, {
        state: { feedbackMessage: t("platformControl.feedback.deploymentCloned", { name: cloned.display_name }) },
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setCloning(false);
    }
  }

  async function handleActivate(): Promise<void> {
    if (!token || !deployment) {
      return;
    }

    setActivating(true);
    setErrorMessage("");
    setFeedbackMessage("");
    try {
      await activateDeploymentProfile(deployment.id, token);
      setFeedbackMessage(t("platformControl.feedback.activationSuccess", { name: deployment.display_name }));
      await reload();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.activationFailed"));
    } finally {
      setActivating(false);
    }
  }

  async function handleDelete(): Promise<void> {
    if (!token || !deployment) {
      return;
    }

    setErrorMessage("");
    setFeedbackMessage("");
    try {
      await deleteDeploymentProfile(deployment.id, token);
      navigate("/control/platform/deployments", {
        state: { feedbackMessage: t("platformControl.feedback.deploymentDeleted") },
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.deploymentDeleteFailed"));
    }
  }

  const combinedFeedback = feedbackMessage || readLocationFeedback(location.state);

  return (
    <PlatformPageLayout
      title={deployment?.display_name ?? t("platformControl.deployments.detailTitle")}
      description={deployment ? t("platformControl.deployments.detailDescription") : t("platformControl.deployments.notFound")}
      errorMessage={errorMessage || loadErrorMessage}
      feedbackMessage={combinedFeedback}
      actions={(
        <Link className="btn btn-secondary" to="/control/platform/deployments">
          {t("platformControl.actions.viewDeployments")}
        </Link>
      )}
    >
      {state === "success" && !deployment ? (
        <article className="panel card-stack">
          <p className="status-text">{t("platformControl.deployments.notFound")}</p>
        </article>
      ) : null}

      {deployment ? (
        <>
          <article className="panel card-stack">
            <div className="platform-card-header">
              <div className="status-row">
                <h3 className="section-title">{deployment.display_name}</h3>
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
                    <th>{t("platformControl.deployments.columns.resources")}</th>
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
                          <Link className="status-text" to={`/control/platform/providers/${binding.provider.id}`}>
                            {binding.provider.slug}
                          </Link>
                        </div>
                      </td>
                      <td>{summarizeBindingResources(binding, t("platformControl.summary.none"))}</td>
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
            <div className="platform-inline-meta">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void handleActivate()}
                disabled={deployment.is_active || activating}
              >
                {deployment.is_active
                  ? t("platformControl.actions.active")
                  : activating
                    ? t("platformControl.actions.activating")
                    : t("platformControl.actions.activate")}
              </button>
            </div>
          </article>

          {form ? (
            <article className="panel card-stack">
              <div className="status-row">
                <h3 className="section-title">{t("platformControl.sections.settings")}</h3>
                <p className="status-text">{t("platformControl.deployments.settingsDescription")}</p>
              </div>
              <PlatformDeploymentForm
                value={form}
                capabilities={requiredCapabilities}
                providersByCapability={providersByCapability}
                modelResourcesByCapability={modelResourcesByCapability}
                helperText={t("platformControl.deployments.editing", { slug: deployment.slug })}
                isSubmitting={saving}
                submitLabel={t("platformControl.actions.saveDeployment")}
                submitBusyLabel={t("platformControl.actions.saving")}
                secondaryAction={{
                  label: t("platformControl.actions.reset"),
                  onClick: () => setForm(buildDeploymentForm(deployment)),
                }}
                onChange={setForm}
                onSubmit={(event) => void handleSave(event)}
              />
            </article>
          ) : null}

          {cloneForm ? (
            <article className="panel card-stack">
              <div className="status-row">
                <h3 className="section-title">{t("platformControl.sections.clone")}</h3>
                <p className="status-text">{t("platformControl.deployments.cloneDescription")}</p>
              </div>
              <form className="card-stack" onSubmit={(event) => void handleClone(event)}>
                <div className="form-grid">
                  <label className="card-stack">
                    <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
                    <input
                      className="field-input"
                      value={cloneForm.slug}
                      onChange={(event) => setCloneForm({ ...cloneForm, slug: event.target.value })}
                    />
                  </label>
                  <label className="card-stack">
                    <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
                    <input
                      className="field-input"
                      value={cloneForm.displayName}
                      onChange={(event) => setCloneForm({ ...cloneForm, displayName: event.target.value })}
                    />
                  </label>
                </div>
                <label className="card-stack">
                  <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
                  <textarea
                    className="field-input quote-admin-textarea"
                    value={cloneForm.description}
                    onChange={(event) => setCloneForm({ ...cloneForm, description: event.target.value })}
                  />
                </label>
                <div className="platform-action-row">
                  <span className="status-text">{t("platformControl.deployments.cloning", { slug: cloneForm.slug })}</span>
                  <button type="submit" className="btn btn-primary" disabled={cloning}>
                    {cloning ? t("platformControl.actions.saving") : t("platformControl.actions.cloneDeployment")}
                  </button>
                </div>
              </form>
            </article>
          ) : null}

          <PlatformDeploymentAuditTable
            entries={deploymentAudit}
            title={t("platformControl.deployments.recentActivations")}
            description={t("platformControl.deployments.recentActivationsDescription")}
          />

          <article className="panel card-stack">
            <div className="status-row">
              <h3 className="section-title">{t("platformControl.sections.danger")}</h3>
              <p className="status-text">{t("platformControl.deployments.deleteDescription")}</p>
            </div>
            <div className="platform-inline-meta">
              {confirmDelete ? (
                <>
                  <button type="button" className="btn btn-secondary" onClick={() => setConfirmDelete(false)}>
                    {t("platformControl.actions.cancel")}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => void handleDelete()}
                    disabled={deployment.is_active}
                  >
                    {t("platformControl.actions.confirmDelete")}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setConfirmDelete(true)}
                  disabled={deployment.is_active}
                >
                  {t("platformControl.actions.delete")}
                </button>
              )}
            </div>
          </article>
        </>
      ) : null}
    </PlatformPageLayout>
  );
}
