import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { listLocalModelArtifacts } from "../../../api/modelops/local";
import { registerExistingManagedModel } from "../../../api/modelops/models";
import type { LocalModelArtifact } from "../../../api/modelops/types";
import { useAuth } from "../../../auth/AuthProvider";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import { TASK_OPTIONS } from "../domain";
import LocalDiscoveryPanel from "../components/LocalDiscoveryPanel";
import LocalDownloadsPanel from "../components/LocalDownloadsPanel";
import LocalArtifactList from "../components/LocalArtifactList";
import { useLocalDownloads } from "../hooks/useLocalDownloads";
import { useLocalModelRegistration } from "../hooks/useLocalModelRegistration";

type LocalModelRegisterView = "discovery" | "downloads" | "manual" | "artifacts";

const LOCAL_MODEL_REGISTER_VIEW_ORDER: ReadonlyArray<LocalModelRegisterView> = [
  "discovery",
  "downloads",
  "manual",
  "artifacts",
];

function resolveLocalModelRegisterView(value: string | null): LocalModelRegisterView {
  if (value === "discovery" || value === "downloads" || value === "manual" || value === "artifacts") {
    return value;
  }
  return "discovery";
}

export default function LocalModelRegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = resolveLocalModelRegisterView(searchParams.get("view"));
  const submenuItems = LOCAL_MODEL_REGISTER_VIEW_ORDER.map((view) => ({
    id: view,
    label: t(`modelOps.local.views.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));
  const { discoveredModels, selectedModelInfo, downloadJobs, hasActiveJobs, feedback, search, inspect, download } =
    useLocalDownloads(token);
  const {
    lastRegisteredModelId,
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
  const [artifacts, setArtifacts] = useState<LocalModelArtifact[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [artifactsError, setArtifactsError] = useState("");
  const [artifactsFeedback, setArtifactsFeedback] = useState("");
  const [registeringArtifactId, setRegisteringArtifactId] = useState("");

  useEffect(() => {
    if (!token || activeView !== "artifacts") {
      return;
    }
    setArtifactsLoading(true);
    setArtifactsError("");
    void listLocalModelArtifacts(token)
      .then(setArtifacts)
      .catch((requestError) => {
        setArtifactsError(requestError instanceof Error ? requestError.message : "Unable to load local artifacts.");
      })
      .finally(() => setArtifactsLoading(false));
  }, [activeView, token]);

  function handleChangeView(view: LocalModelRegisterView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  return (
    <ModelOpsWorkspaceFrame
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("modelOps.local.views.aria")} />}
    >
      <section className="card-stack">
        {activeView === "discovery" ? (
          <LocalDiscoveryPanel
            taskKey={discoveryTaskKey}
            query={discoverQuery}
            feedback={feedback}
            discoveredModels={discoveredModels}
            selectedModelInfo={selectedModelInfo}
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
        ) : null}

        {activeView === "downloads" ? (
          <LocalDownloadsPanel
            downloadJobs={downloadJobs}
            hasActiveJobs={hasActiveJobs}
          />
        ) : null}

        {activeView === "manual" ? (
          <>
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

            {lastRegisteredModelId && (
              <div className="button-row">
                <Link className="btn btn-secondary" to={`/control/models/${encodeURIComponent(lastRegisteredModelId)}/test`}>
                  {t("modelOps.actions.testModel")}
                </Link>
              </div>
            )}
          </>
        ) : null}

        {activeView === "artifacts" ? (
          <>
            <article className="panel card-stack">
              <h2 className="section-title">{t("modelOps.artifacts.title")}</h2>
              <p className="status-text">{t("modelOps.artifacts.description")}</p>
              {artifactsLoading ? (
                <p className="status-text">{t("modelOps.states.loading")}</p>
              ) : (
                <LocalArtifactList
                  artifacts={artifacts}
                  registeringArtifactId={registeringArtifactId}
                  onRegister={async (artifact) => {
                    if (!token || !artifact.suggested_model_id) {
                      return;
                    }
                    setRegisteringArtifactId(artifact.artifact_id);
                    setArtifactsError("");
                    setArtifactsFeedback("");
                    try {
                      await registerExistingManagedModel(artifact.suggested_model_id, token);
                      setArtifacts(await listLocalModelArtifacts(token));
                      setArtifactsFeedback(t("modelOps.artifacts.registered"));
                    } catch (requestError) {
                      setArtifactsError(requestError instanceof Error ? requestError.message : t("modelOps.artifacts.registerFailed"));
                    } finally {
                      setRegisteringArtifactId("");
                    }
                  }}
                />
              )}
            </article>
            {artifactsFeedback && <p className="status-text">{artifactsFeedback}</p>}
            {artifactsError && <p className="error-text">{artifactsError}</p>}
          </>
        ) : null}
      </section>
    </ModelOpsWorkspaceFrame>
  );
}
