import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { CloudDiscoveredModel, ModelCredential } from "../../../api/modelops/types";
import { CLOUD_PROVIDER_OPTIONS, TASK_OPTIONS } from "../domain";

type CloudAccessMode = "personal_private" | "platform_shared";

type CloudModelRegistrationState = {
  id: string;
  name: string;
  provider: string;
  accessMode: CloudAccessMode;
  providerModelId: string;
  credentialId: string;
  taskKey: string;
  comment: string;
};

type CloudModelRegistrationFormProps = {
  state: CloudModelRegistrationState;
  credentials: ModelCredential[];
  discoveredModels: CloudDiscoveredModel[];
  isLoading: boolean;
  isSaving: boolean;
  isDiscovering: boolean;
  allowPlatformOwnership: boolean;
  actorUserId?: number | null;
  onChange: (next: CloudModelRegistrationState) => void;
  onDiscover: (provider: string, credentialId: string) => Promise<CloudDiscoveredModel[]>;
  onClearDiscovery: () => void;
  onSubmit: () => Promise<void>;
};

function ownerTypeForAccessMode(mode: CloudAccessMode): "platform" | "user" {
  return mode === "platform_shared" ? "platform" : "user";
}

function sanitizeModelIdPart(value: string, fallback: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || fallback;
}

function generatedModelId(
  provider: string,
  ownerType: "platform" | "user",
  actorUserId: number | null | undefined,
  providerModelId: string,
): string {
  const providerPart = sanitizeModelIdPart(provider, "provider");
  const modelPart = sanitizeModelIdPart(providerModelId, "model");
  if (ownerType === "user") {
    return `${providerPart}-user-${actorUserId ?? "current"}-${modelPart}`;
  }
  return `${providerPart}-${modelPart}`;
}

function categoryForTask(taskKey: string): "predictive" | "generative" {
  return TASK_OPTIONS.find((option) => option.value === taskKey)?.category ?? "generative";
}

function taskLabel(taskKey: string): string {
  return TASK_OPTIONS.find((option) => option.value === taskKey)?.label ?? taskKey;
}

export default function CloudModelRegistrationForm({
  state,
  credentials,
  discoveredModels,
  isLoading,
  isSaving,
  isDiscovering,
  allowPlatformOwnership,
  actorUserId,
  onChange,
  onDiscover,
  onClearDiscovery,
  onSubmit,
}: CloudModelRegistrationFormProps): JSX.Element {
  const { t } = useTranslation("common");
  const [hasBrowsedModels, setHasBrowsedModels] = useState(false);
  const [modelSearchQuery, setModelSearchQuery] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [taskFilter, setTaskFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const providerLabel = useMemo(() => {
    const option = CLOUD_PROVIDER_OPTIONS.find((candidate) => candidate.value === state.provider);
    return option ? t(option.labelKey) : state.provider;
  }, [state.provider, t]);

  const filteredCredentials = useMemo(
    () => credentials.filter((credential) => credential.provider === state.provider),
    [credentials, state.provider],
  );
  const selectedCredential = filteredCredentials.find((credential) => credential.id === state.credentialId) ?? null;
  const selectedModel = discoveredModels.find((model) => model.provider_model_id === state.providerModelId) ?? null;
  const hasCredentialsForProvider = filteredCredentials.length > 0;
  const canBrowseModels = Boolean(state.provider && state.credentialId);
  const taskIsEditable = selectedModel?.task_key !== "embeddings";
  const canSubmit = Boolean(selectedModel && state.id.trim() && state.name.trim() && state.providerModelId.trim() && state.credentialId);
  const modelOwnerOptions = useMemo(
    () => Array.from(new Set(discoveredModels.map((model) => model.owned_by?.trim()).filter(Boolean) as string[])).sort(),
    [discoveredModels],
  );
  const modelTaskOptions = useMemo(
    () => Array.from(new Set(discoveredModels.map((model) => model.task_key).filter(Boolean))).sort(),
    [discoveredModels],
  );
  const modelCategoryOptions = useMemo(
    () => Array.from(new Set(discoveredModels.map((model) => model.category ?? categoryForTask(model.task_key)).filter(Boolean))).sort(),
    [discoveredModels],
  );
  const filteredDiscoveredModels = useMemo(() => {
    const normalizedQuery = modelSearchQuery.trim().toLowerCase();
    return discoveredModels.filter((model) => {
      const category = model.category ?? categoryForTask(model.task_key);
      const owner = model.owned_by?.trim() || "";
      const matchesQuery = !normalizedQuery
        || model.provider_model_id.toLowerCase().includes(normalizedQuery)
        || model.name.toLowerCase().includes(normalizedQuery);
      return matchesQuery
        && (!ownerFilter || owner === ownerFilter)
        && (!taskFilter || model.task_key === taskFilter)
        && (!categoryFilter || category === categoryFilter);
    });
  }, [categoryFilter, discoveredModels, modelSearchQuery, ownerFilter, taskFilter]);

  function resetSelection(next: CloudModelRegistrationState): CloudModelRegistrationState {
    return {
      ...next,
      id: "",
      name: "",
      providerModelId: "",
      taskKey: "llm",
    };
  }

  function handleProviderChange(provider: string): void {
    setHasBrowsedModels(false);
    setModelSearchQuery("");
    setOwnerFilter("");
    setTaskFilter("");
    setCategoryFilter("");
    onClearDiscovery();
    onChange(resetSelection({ ...state, provider, credentialId: "" }));
  }

  function handleCredentialChange(credentialId: string): void {
    setHasBrowsedModels(false);
    setModelSearchQuery("");
    setOwnerFilter("");
    setTaskFilter("");
    setCategoryFilter("");
    onClearDiscovery();
    onChange(resetSelection({ ...state, credentialId }));
  }

  function handleAccessModeChange(mode: CloudAccessMode): void {
    const ownerType = ownerTypeForAccessMode(mode);
    const nextState = {
      ...state,
      accessMode: mode,
    };
    onChange(
      selectedModel
        ? {
          ...nextState,
          id: generatedModelId(state.provider, ownerType, actorUserId, selectedModel.provider_model_id),
        }
        : nextState,
    );
  }

  async function handleBrowseProviderModels(): Promise<void> {
    setHasBrowsedModels(true);
    await onDiscover(state.provider, state.credentialId);
  }

  function handleSelectModel(model: CloudDiscoveredModel): void {
    const nextTaskKey = model.task_key || "llm";
    onChange({
      ...state,
      id: generatedModelId(state.provider, ownerTypeForAccessMode(state.accessMode), actorUserId, model.provider_model_id),
      name: model.provider_model_id,
      providerModelId: model.provider_model_id,
      taskKey: nextTaskKey,
    });
  }

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.cloud.registrationTitle")}</h2>

      <section className="panel panel-nested card-stack" aria-labelledby="cloud-registration-step-provider">
        <h3 id="cloud-registration-step-provider" className="section-title">{t("modelOps.cloud.providerStepTitle")}</h3>
        <label className="field-label" htmlFor="cloud-model-provider">{t("modelOps.fields.provider")}</label>
        <select
          id="cloud-model-provider"
          className="field-input"
          value={state.provider}
          onChange={(event) => handleProviderChange(event.currentTarget.value)}
        >
          <option value="">{t("modelOps.cloud.selectProvider")}</option>
          {CLOUD_PROVIDER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
          ))}
        </select>
      </section>

      {state.provider ? (
        <section className="panel panel-nested card-stack" aria-labelledby="cloud-registration-step-credential">
          <h3 id="cloud-registration-step-credential" className="section-title">{t("modelOps.cloud.credentialStepTitle")}</h3>
          {isLoading ? <p className="status-text">{t("modelOps.states.loading")}</p> : null}
          {!isLoading && !hasCredentialsForProvider ? (
            <p className="status-text">
              {t("modelOps.cloud.noCredentialsForProvider")}{" "}
              <Link to={`?view=credentials&provider=${encodeURIComponent(state.provider)}`}>
                {t("modelOps.cloud.saveCredentialForProvider", { provider: providerLabel })}
              </Link>
            </p>
          ) : null}
          {hasCredentialsForProvider ? (
            <>
              <label className="field-label" htmlFor="cloud-credential-id">{t("modelOps.fields.credential")}</label>
              <select
                id="cloud-credential-id"
                className="field-input"
                value={state.credentialId}
                onChange={(event) => handleCredentialChange(event.currentTarget.value)}
              >
                <option value="">{t("modelOps.cloud.selectCredential")}</option>
                {filteredCredentials.map((credential) => (
                  <option key={credential.id} value={credential.id}>
                    {`${credential.display_name} · ****${credential.api_key_last4}`}
                  </option>
                ))}
              </select>
            </>
          ) : null}
        </section>
      ) : null}

      {state.provider && selectedCredential ? (
        <section className="panel panel-nested card-stack" aria-labelledby="cloud-registration-step-access">
          <h3 id="cloud-registration-step-access" className="section-title">{t("modelOps.cloud.accessStepTitle")}</h3>
          {allowPlatformOwnership ? (
            <>
              <label className="field-label" htmlFor="cloud-model-access-mode">{t("modelOps.fields.accessMode")}</label>
              <select
                id="cloud-model-access-mode"
                className="field-input"
                value={state.accessMode}
                onChange={(event) => handleAccessModeChange(event.currentTarget.value as CloudAccessMode)}
              >
                <option value="personal_private">{t("modelOps.cloud.accessModes.personalPrivate")}</option>
                <option value="platform_shared">{t("modelOps.cloud.accessModes.platformShared")}</option>
              </select>
              <p className="status-text">{t(`modelOps.cloud.accessModeDescriptions.${state.accessMode}`)}</p>
            </>
          ) : (
            <p className="status-text">
              {t("modelOps.cloud.personalPrivateAccess")}
            </p>
          )}
        </section>
      ) : null}

      {canBrowseModels ? (
        <section className="panel panel-nested card-stack" aria-labelledby="cloud-registration-step-discovery">
          <h3 id="cloud-registration-step-discovery" className="section-title">{t("modelOps.cloud.discoveryStepTitle")}</h3>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isDiscovering}
            onClick={() => void handleBrowseProviderModels()}
          >
            {isDiscovering ? t("modelOps.cloud.browsingProviderModels") : t("modelOps.cloud.browseProviderModels")}
          </button>
          {hasBrowsedModels && !isDiscovering && discoveredModels.length === 0 ? (
            <p className="status-text">{t("modelOps.cloud.noDiscoveredModels")}</p>
          ) : null}
          {discoveredModels.length > 0 ? (
            <>
              <div className="modelops-filter-grid">
                <label className="card-stack" htmlFor="cloud-model-search">
                  <span className="field-label">{t("modelOps.cloud.searchModels")}</span>
                  <input
                    id="cloud-model-search"
                    className="field-input"
                    value={modelSearchQuery}
                    onChange={(event) => setModelSearchQuery(event.currentTarget.value)}
                  />
                </label>
                <label className="card-stack" htmlFor="cloud-model-owner-filter">
                  <span className="field-label">{t("modelOps.cloud.ownerFilter")}</span>
                  <select
                    id="cloud-model-owner-filter"
                    className="field-input"
                    value={ownerFilter}
                    onChange={(event) => setOwnerFilter(event.currentTarget.value)}
                  >
                    <option value="">{t("modelOps.cloud.allOwners")}</option>
                    {modelOwnerOptions.map((owner) => (
                      <option key={owner} value={owner}>{owner}</option>
                    ))}
                  </select>
                </label>
                <label className="card-stack" htmlFor="cloud-model-task-filter">
                  <span className="field-label">{t("modelOps.cloud.taskFilter")}</span>
                  <select
                    id="cloud-model-task-filter"
                    className="field-input"
                    value={taskFilter}
                    onChange={(event) => setTaskFilter(event.currentTarget.value)}
                  >
                    <option value="">{t("modelOps.cloud.allTasks")}</option>
                    {modelTaskOptions.map((task) => (
                      <option key={task} value={task}>{taskLabel(task)}</option>
                    ))}
                  </select>
                </label>
                <label className="card-stack" htmlFor="cloud-model-category-filter">
                  <span className="field-label">{t("modelOps.cloud.categoryFilter")}</span>
                  <select
                    id="cloud-model-category-filter"
                    className="field-input"
                    value={categoryFilter}
                    onChange={(event) => setCategoryFilter(event.currentTarget.value)}
                  >
                    <option value="">{t("modelOps.cloud.allCategories")}</option>
                    {modelCategoryOptions.map((category) => (
                      <option key={category} value={category}>{category}</option>
                    ))}
                  </select>
                </label>
              </div>
              <p className="status-text">
                {t("modelOps.cloud.modelFilterResultCount", {
                  count: filteredDiscoveredModels.length,
                  total: discoveredModels.length,
                })}
              </p>
              {filteredDiscoveredModels.length === 0 ? (
                <p className="status-text">{t("modelOps.cloud.noFilteredModels")}</p>
              ) : (
                <ul className="card-stack" aria-label={t("modelOps.cloud.discoveredModelsListAria")}>
                  {filteredDiscoveredModels.map((model) => (
                    <li key={model.provider_model_id} className="panel panel-nested card-stack">
                      <div className="modelops-card-header">
                        <div className="card-stack">
                          <strong>{model.name || model.provider_model_id}</strong>
                          <span className="status-text">{model.provider_model_id}</span>
                        </div>
                        <button
                          type="button"
                          className={state.providerModelId === model.provider_model_id ? "btn btn-primary" : "btn btn-secondary"}
                          onClick={() => handleSelectModel(model)}
                        >
                          {state.providerModelId === model.provider_model_id
                            ? t("modelOps.cloud.selectedProviderModel")
                            : t("modelOps.cloud.selectProviderModel")}
                        </button>
                      </div>
                      <p className="status-text">
                        {t("modelOps.cloud.discoveredModelSummary", {
                          owner: model.owned_by || t("modelOps.states.unknown"),
                          task: taskLabel(model.task_key),
                          category: model.category ?? categoryForTask(model.task_key),
                        })}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : null}
        </section>
      ) : null}

      {selectedModel ? (
        <section className="panel panel-nested card-stack" aria-labelledby="cloud-registration-step-review">
          <h3 id="cloud-registration-step-review" className="section-title">{t("modelOps.cloud.reviewStepTitle")}</h3>
          <label className="field-label" htmlFor="cloud-model-id">{t("modelOps.cloud.generatedModelId")}</label>
          <input
            id="cloud-model-id"
            className="field-input"
            value={state.id}
            readOnly
          />
          <label className="field-label" htmlFor="cloud-provider-model-id">{t("modelOps.fields.providerModelId")}</label>
          <input
            id="cloud-provider-model-id"
            className="field-input"
            value={state.providerModelId}
            readOnly
          />
          <label className="field-label" htmlFor="cloud-model-name">{t("modelOps.fields.modelName")}</label>
          <input
            id="cloud-model-name"
            className="field-input"
            value={state.name}
            onChange={(event) => onChange({ ...state, name: event.currentTarget.value })}
          />
          <label className="field-label" htmlFor="cloud-model-task">{t("modelOps.cloud.inferredTask")}</label>
          <select
            id="cloud-model-task"
            className="field-input"
            value={state.taskKey}
            disabled={!taskIsEditable}
            onChange={(event) => onChange({ ...state, taskKey: event.currentTarget.value })}
          >
            {TASK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          {taskIsEditable ? <p className="status-text">{t("modelOps.cloud.taskReviewHint")}</p> : null}
          <label className="field-label" htmlFor="cloud-model-comment">{t("modelOps.fields.comment")}</label>
          <input
            id="cloud-model-comment"
            className="field-input"
            value={state.comment}
            onChange={(event) => onChange({ ...state, comment: event.currentTarget.value })}
          />
          <button type="button" className="btn btn-primary" disabled={isSaving || !canSubmit} onClick={() => void onSubmit()}>
            {t("modelOps.actions.registerCloud")}
          </button>
        </section>
      ) : null}
    </article>
  );
}
