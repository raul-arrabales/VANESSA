import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { registerManagedModel, validateManagedModel } from "../../../api/models";
import { useAuth } from "../../../auth/AuthProvider";
import { TASK_OPTIONS } from "../constants";
import LocalDiscoveryPanel from "../components/LocalDiscoveryPanel";
import { useLocalDownloads } from "../hooks/useLocalDownloads";

export default function LocalModelRegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { discoveredModels, selectedModelInfo, downloadJobs, hasActiveJobs, error, feedback, search, inspect, download } =
    useLocalDownloads(token);

  const [discoveryTaskKey, setDiscoveryTaskKey] = useState("llm");
  const [discoverQuery, setDiscoverQuery] = useState("");
  const [manualState, setManualState] = useState({
    id: "",
    name: "",
    provider: "local",
    localPath: "",
    taskKey: "llm",
    comment: "",
    validateAfterRegister: false,
  });
  const [manualFeedback, setManualFeedback] = useState("");
  const [manualError, setManualError] = useState("");

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.local.title")}</h2>
        <p className="status-text">{t("modelOps.local.description")}</p>
        <div className="button-row">
          <Link className="btn btn-secondary" to="/control/models/local/artifacts">
            {t("modelOps.actions.viewArtifacts")}
          </Link>
        </div>
      </article>

      <LocalDiscoveryPanel
        taskKey={discoveryTaskKey}
        query={discoverQuery}
        discoveredModels={discoveredModels}
        selectedModelInfo={selectedModelInfo}
        downloadJobs={downloadJobs}
        hasActiveJobs={hasActiveJobs}
        onTaskKeyChange={setDiscoveryTaskKey}
        onQueryChange={setDiscoverQuery}
        onSearch={() => search({ query: discoverQuery, task_key: discoveryTaskKey })}
        onInspect={inspect}
        onDownload={(model) => download(
          model,
          discoveryTaskKey,
          TASK_OPTIONS.find((option) => option.value === discoveryTaskKey)?.category,
        )}
      />

      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.local.manualTitle")}</h2>
        <div className="control-group">
          <label className="field-label" htmlFor="local-model-id">{t("modelOps.fields.modelId")}</label>
          <input id="local-model-id" className="field-input" value={manualState.id} onChange={(event) => setManualState({ ...manualState, id: event.currentTarget.value })} />
          <label className="field-label" htmlFor="local-model-name">{t("modelOps.fields.modelName")}</label>
          <input id="local-model-name" className="field-input" value={manualState.name} onChange={(event) => setManualState({ ...manualState, name: event.currentTarget.value })} />
          <label className="field-label" htmlFor="local-model-provider">{t("modelOps.fields.provider")}</label>
          <input id="local-model-provider" className="field-input" value={manualState.provider} onChange={(event) => setManualState({ ...manualState, provider: event.currentTarget.value })} />
          <label className="field-label" htmlFor="local-model-path">{t("modelOps.fields.localPath")}</label>
          <input id="local-model-path" className="field-input" value={manualState.localPath} onChange={(event) => setManualState({ ...manualState, localPath: event.currentTarget.value })} />
          <label className="field-label" htmlFor="local-model-task">{t("modelOps.fields.task")}</label>
          <select id="local-model-task" className="field-input" value={manualState.taskKey} onChange={(event) => setManualState({ ...manualState, taskKey: event.currentTarget.value })}>
            {TASK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <label className="field-label" htmlFor="local-model-comment">{t("modelOps.fields.comment")}</label>
          <input id="local-model-comment" className="field-input" value={manualState.comment} onChange={(event) => setManualState({ ...manualState, comment: event.currentTarget.value })} />
          <label className="status-row">
            <input
              type="checkbox"
              checked={manualState.validateAfterRegister}
              onChange={(event) => setManualState({ ...manualState, validateAfterRegister: event.currentTarget.checked })}
            />
            <span>{t("modelOps.actions.validateAfterRegister")}</span>
          </label>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              if (!token) {
                return;
              }
              const category = TASK_OPTIONS.find((option) => option.value === manualState.taskKey)?.category ?? "generative";
              void registerManagedModel(
                {
                  id: manualState.id.trim(),
                  name: manualState.name.trim(),
                  provider: manualState.provider.trim() || "local",
                  backend: "local",
                  owner_type: "platform",
                  source: "local_folder",
                  availability: "offline_ready",
                  visibility_scope: "platform",
                  local_path: manualState.localPath.trim(),
                  task_key: manualState.taskKey,
                  category,
                  comment: manualState.comment.trim() || undefined,
                },
                token,
              )
                .then(async (model) => {
                  if (manualState.validateAfterRegister) {
                    await validateManagedModel(model.id, token);
                  }
                  setManualFeedback(t("modelOps.local.manualSuccess"));
                  setManualError("");
                  setManualState({
                    id: "",
                    name: "",
                    provider: "local",
                    localPath: "",
                    taskKey: "llm",
                    comment: "",
                    validateAfterRegister: false,
                  });
                })
                .catch((requestError) => {
                  setManualError(requestError instanceof Error ? requestError.message : t("modelOps.local.manualFailure"));
                });
            }}
          >
            {t("modelOps.actions.registerLocal")}
          </button>
        </div>
      </article>

      {feedback && <p className="status-text">{feedback}</p>}
      {manualFeedback && <p className="status-text">{manualFeedback}</p>}
      {(error || manualError) && <p className="error-text">{error || manualError}</p>}
    </section>
  );
}
