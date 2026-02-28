import { useEffect, useMemo, useState } from "react";
import {
  createModelCredential,
  listAvailableManagedModels,
  listModelCredentials,
  registerManagedModel,
  revokeModelCredential,
  type ManagedModel,
  type ModelCredential,
} from "../api/models";
import { useAuth } from "../auth/AuthProvider";

export default function ModelAccessPage(): JSX.Element {
  const { token, user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";

  const [credentials, setCredentials] = useState<ModelCredential[]>([]);
  const [models, setModels] = useState<ManagedModel[]>([]);
  const [feedback, setFeedback] = useState("");

  const [displayName, setDisplayName] = useState("");
  const [provider, setProvider] = useState("openai_compatible");
  const [apiBaseUrl, setApiBaseUrl] = useState("https://api.openai.com/v1");
  const [apiKey, setApiKey] = useState("");
  const [credentialScope, setCredentialScope] = useState<"platform" | "personal">("personal");

  const [modelId, setModelId] = useState("");
  const [modelName, setModelName] = useState("");
  const [modelBackend, setModelBackend] = useState<"external_api" | "local">("external_api");
  const [modelOrigin, setModelOrigin] = useState<"platform" | "personal">("personal");
  const [providerModelId, setProviderModelId] = useState("");
  const [credentialId, setCredentialId] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [comment, setComment] = useState("");

  const availableCredentialOptions = useMemo(() => (
    credentials.filter((credential) => credential.provider === provider)
  ), [credentials, provider]);

  const refreshData = async (): Promise<void> => {
    if (!token) {
      return;
    }
    const [credentialRows, modelRows] = await Promise.all([
      listModelCredentials(token),
      listAvailableManagedModels(token),
    ]);
    setCredentials(credentialRows);
    setModels(modelRows);
  };

  useEffect(() => {
    if (!token) {
      return;
    }
    void refreshData().catch((error) => {
      setFeedback(error instanceof Error ? error.message : "Unable to load model management data.");
    });
  }, [token]);

  const handleCreateCredential = async (): Promise<void> => {
    if (!token || !apiKey.trim()) {
      return;
    }
    try {
      await createModelCredential(
        {
          provider,
          display_name: displayName.trim() || `${provider}-key`,
          api_base_url: apiBaseUrl.trim() || undefined,
          api_key: apiKey,
          credential_scope: isSuperadmin ? credentialScope : "personal",
        },
        token,
      );
      setApiKey("");
      setDisplayName("");
      await refreshData();
      setFeedback("Credential saved.");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Unable to save credential.");
    }
  };

  const handleRegisterModel = async (): Promise<void> => {
    if (!token || !modelId.trim() || !modelName.trim()) {
      return;
    }
    try {
      await registerManagedModel(
        {
          id: modelId.trim(),
          name: modelName.trim(),
          provider,
          backend: modelBackend,
          origin: isSuperadmin ? modelOrigin : "personal",
          source: modelBackend === "external_api" ? "external_provider" : "local_folder",
          availability: modelBackend === "external_api" ? "online_only" : "offline_ready",
          access_scope: modelOrigin === "personal" ? "private" : "assigned",
          provider_model_id: modelBackend === "external_api" ? providerModelId.trim() : undefined,
          credential_id: modelBackend === "external_api" ? credentialId || undefined : undefined,
          local_path: modelBackend === "local" ? localPath.trim() || undefined : undefined,
          comment: comment.trim() || undefined,
        },
        token,
      );
      setModelId("");
      setModelName("");
      setProviderModelId("");
      setLocalPath("");
      setComment("");
      await refreshData();
      setFeedback("Model registered.");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Unable to register model.");
    }
  };

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">Model credentials</h2>
        <p className="status-text">Create API credentials (keys are never shown again; only last4 is displayed).</p>
        <div className="control-group">
          <label className="field-label" htmlFor="credential-provider">Provider</label>
          <select id="credential-provider" className="field-input" value={provider} onChange={(event) => setProvider(event.currentTarget.value)}>
            <option value="openai_compatible">OpenAI-compatible</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
          </select>
          {isSuperadmin && (
            <>
              <label className="field-label" htmlFor="credential-scope">Credential scope</label>
              <select id="credential-scope" className="field-input" value={credentialScope} onChange={(event) => setCredentialScope(event.currentTarget.value as "platform" | "personal") }>
                <option value="personal">Personal</option>
                <option value="platform">Platform</option>
              </select>
            </>
          )}
          <label className="field-label" htmlFor="credential-display-name">Display name</label>
          <input id="credential-display-name" className="field-input" value={displayName} onChange={(event) => setDisplayName(event.currentTarget.value)} />
          <label className="field-label" htmlFor="credential-base-url">API base URL</label>
          <input id="credential-base-url" className="field-input" value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.currentTarget.value)} />
          <label className="field-label" htmlFor="credential-api-key">API key</label>
          <input id="credential-api-key" type="password" className="field-input" value={apiKey} onChange={(event) => setApiKey(event.currentTarget.value)} />
          <button type="button" className="btn btn-primary" onClick={() => void handleCreateCredential()}>Save credential</button>
        </div>
        <ul className="card-stack" aria-label="Credentials list">
          {credentials.map((credential) => (
            <li key={credential.id} className="status-row">
              <span>{credential.display_name} · {credential.provider} · ****{credential.api_key_last4}</span>
              <button type="button" className="btn btn-ghost" onClick={() => {
                if (!token) return;
                void revokeModelCredential(credential.id, token)
                  .then(() => refreshData())
                  .catch((error) => setFeedback(error instanceof Error ? error.message : "Unable to revoke credential."));
              }}>Revoke</button>
            </li>
          ))}
        </ul>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Register model</h2>
        <div className="control-group">
          <label className="field-label" htmlFor="managed-model-id">Model id</label>
          <input id="managed-model-id" className="field-input" value={modelId} onChange={(event) => setModelId(event.currentTarget.value)} />
          <label className="field-label" htmlFor="managed-model-name">Model name</label>
          <input id="managed-model-name" className="field-input" value={modelName} onChange={(event) => setModelName(event.currentTarget.value)} />
          {isSuperadmin && (
            <>
              <label className="field-label" htmlFor="managed-model-origin">Origin</label>
              <select id="managed-model-origin" className="field-input" value={modelOrigin} onChange={(event) => setModelOrigin(event.currentTarget.value as "platform" | "personal") }>
                <option value="personal">Personal</option>
                <option value="platform">Platform</option>
              </select>
            </>
          )}
          <label className="field-label" htmlFor="managed-model-backend">Backend</label>
          <select id="managed-model-backend" className="field-input" value={modelBackend} onChange={(event) => setModelBackend(event.currentTarget.value as "external_api" | "local") }>
            <option value="external_api">External API</option>
            <option value="local">Local</option>
          </select>
          {modelBackend === "external_api" ? (
            <>
              <label className="field-label" htmlFor="managed-provider-model-id">Provider model id</label>
              <input id="managed-provider-model-id" className="field-input" value={providerModelId} onChange={(event) => setProviderModelId(event.currentTarget.value)} />
              <label className="field-label" htmlFor="managed-credential-id">Credential</label>
              <select id="managed-credential-id" className="field-input" value={credentialId} onChange={(event) => setCredentialId(event.currentTarget.value)}>
                <option value="">Select credential</option>
                {availableCredentialOptions.map((credential) => (
                  <option key={credential.id} value={credential.id}>{credential.display_name} · ****{credential.api_key_last4}</option>
                ))}
              </select>
            </>
          ) : (
            <>
              <label className="field-label" htmlFor="managed-local-path">Local path</label>
              <input id="managed-local-path" className="field-input" value={localPath} onChange={(event) => setLocalPath(event.currentTarget.value)} />
            </>
          )}
          <label className="field-label" htmlFor="managed-comment">Comment</label>
          <input id="managed-comment" className="field-input" value={comment} onChange={(event) => setComment(event.currentTarget.value)} />
          <button type="button" className="btn btn-primary" onClick={() => void handleRegisterModel()}>Register model</button>
        </div>
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">Available models</h2>
        <ul className="card-stack" aria-label="Available models list">
          {models.map((model) => (
            <li key={model.id}>
              <strong>{model.name}</strong>
              <p className="status-text">{model.id} · {model.origin} · {model.backend} · {model.provider} · {model.availability}</p>
            </li>
          ))}
        </ul>
      </article>

      {feedback && <p className="status-text">{feedback}</p>}
    </section>
  );
}
