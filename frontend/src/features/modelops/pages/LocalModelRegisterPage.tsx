import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import { TASK_OPTIONS } from "../domain";
import LocalDiscoveryPanel from "../components/LocalDiscoveryPanel";
import { useLocalDownloads } from "../hooks/useLocalDownloads";
import { useLocalModelRegistration } from "../hooks/useLocalModelRegistration";

export default function LocalModelRegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { discoveredModels, selectedModelInfo, downloadJobs, hasActiveJobs, feedback, search, inspect, download } =
    useLocalDownloads(token);
  const {
    lastRegisteredModelId,
    feedback: manualFeedback,
    registerLocalModel,
  } = useLocalModelRegistration(token);

  const [discoveryTaskKey, setDiscoveryTaskKey] = useState("llm");
  const [discoverQuery, setDiscoverQuery] = useState("");
  const [manualState, setManualState] = useState({
    id: "",
    name: "",
    provider: "local",
    localPath: "",
    taskKey: "llm",
    comment: "",
  });
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
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              const category = TASK_OPTIONS.find((option) => option.value === manualState.taskKey)?.category ?? "generative";
              void registerLocalModel({
                id: manualState.id,
                name: manualState.name,
                provider: manualState.provider,
                localPath: manualState.localPath,
                taskKey: manualState.taskKey,
                category,
                comment: manualState.comment,
              }).then((didRegister) => {
                if (didRegister) {
                  setManualState({
                    id: "",
                    name: "",
                    provider: "local",
                    localPath: "",
                    taskKey: "llm",
                    comment: "",
                  });
                }
              });
            }}
          >
            {t("modelOps.actions.registerLocal")}
          </button>
        </div>
      </article>

      {feedback && <p className="status-text">{feedback}</p>}
      {manualFeedback && <p className="status-text">{manualFeedback}</p>}
      {lastRegisteredModelId && (
        <div className="button-row">
          <Link className="btn btn-secondary" to={`/control/models/${encodeURIComponent(lastRegisteredModelId)}/test`}>
            {t("modelOps.actions.testModel")}
          </Link>
        </div>
      )}
    </section>
  );
}
