import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listLocalModelArtifacts } from "../../../api/modelops/local";
import { registerExistingManagedModel } from "../../../api/modelops/models";
import type { LocalModelArtifact } from "../../../api/modelops/types";
import LocalArtifactList from "./LocalArtifactList";

type LocalArtifactsPanelProps = {
  token: string;
};

export default function LocalArtifactsPanel({
  token,
}: LocalArtifactsPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const [artifacts, setArtifacts] = useState<LocalModelArtifact[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [artifactsError, setArtifactsError] = useState("");
  const [artifactsFeedback, setArtifactsFeedback] = useState("");
  const [registeringArtifactId, setRegisteringArtifactId] = useState("");

  useEffect(() => {
    if (!token) {
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
  }, [token]);

  async function handleRegisterArtifact(artifact: LocalModelArtifact): Promise<void> {
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
  }

  return (
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
            onRegister={handleRegisterArtifact}
          />
        )}
      </article>
      {artifactsFeedback && <p className="status-text">{artifactsFeedback}</p>}
      {artifactsError && <p className="error-text">{artifactsError}</p>}
    </>
  );
}
