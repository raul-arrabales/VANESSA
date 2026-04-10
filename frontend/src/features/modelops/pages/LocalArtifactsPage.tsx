import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { registerExistingManagedModel } from "../../../api/modelops/models";
import { listLocalModelArtifacts } from "../../../api/modelops/local";
import type { LocalModelArtifact } from "../../../api/modelops/types";
import { useAuth } from "../../../auth/AuthProvider";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import LocalArtifactList from "../components/LocalArtifactList";

export default function LocalArtifactsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const [artifacts, setArtifacts] = useState<LocalModelArtifact[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [registeringArtifactId, setRegisteringArtifactId] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    setError("");
    void listLocalModelArtifacts(token)
      .then(setArtifacts)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "Unable to load local artifacts.");
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  return (
    <ModelOpsWorkspaceFrame>
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.artifacts.title")}</h2>
        <p className="status-text">{t("modelOps.artifacts.description")}</p>
        {isLoading ? (
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
              setError("");
              setFeedback("");
              try {
                await registerExistingManagedModel(artifact.suggested_model_id, token);
                setArtifacts(await listLocalModelArtifacts(token));
                setFeedback(t("modelOps.artifacts.registered"));
              } catch (requestError) {
                setError(requestError instanceof Error ? requestError.message : t("modelOps.artifacts.registerFailed"));
              } finally {
                setRegisteringArtifactId("");
              }
            }}
          />
        )}
      </article>
      {feedback && <p className="status-text">{feedback}</p>}
      {error && <p className="error-text">{error}</p>}
    </ModelOpsWorkspaceFrame>
  );
}
