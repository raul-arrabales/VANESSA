import { useEffect, useState } from "react";
import { listEnabledModels, runInference, type ModelCatalogItem } from "../api/models";
import { useAuth } from "../auth/AuthProvider";

export default function ChatbotPage(): JSX.Element {
  const { token, isAuthenticated } = useAuth();
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAuthenticated || !token) {
      return;
    }

    const loadModels = async (): Promise<void> => {
      try {
        const enabledModels = await listEnabledModels(token);
        setModels(enabledModels);
        setSelectedModel(enabledModels[0]?.id ?? "");
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to load models.");
      }
    };

    void loadModels();
  }, [isAuthenticated, token]);

  const submitPrompt = async (): Promise<void> => {
    if (!token || !selectedModel || !prompt.trim()) {
      return;
    }

    setError("");

    try {
      const result = await runInference(prompt.trim(), selectedModel, token);
      setOutput(result.output);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Inference request failed.");
    }
  };

  return (
    <section className="panel card-stack" aria-label="Chatbot panel">
      <h2 className="section-title">Chatbot</h2>
      <p className="status-text">Run inference with models enabled for your current account.</p>

      <label className="field-label" htmlFor="model-picker">Model</label>
      <select
        id="model-picker"
        className="field-input"
        value={selectedModel}
        onChange={(event) => setSelectedModel(event.currentTarget.value)}
        disabled={models.length === 0}
      >
        {models.length === 0 && <option value="">No enabled models</option>}
        {models.map((model) => (
          <option key={model.id} value={model.id}>{model.name}</option>
        ))}
      </select>

      <label className="field-label" htmlFor="prompt">Prompt</label>
      <textarea
        id="prompt"
        className="field-input"
        value={prompt}
        onChange={(event) => setPrompt(event.currentTarget.value)}
        rows={4}
      />

      <button type="button" className="btn btn-primary" onClick={() => void submitPrompt()} disabled={!selectedModel}>
        Send prompt
      </button>

      {output && <pre className="code-block">{output}</pre>}
      {error && <p className="status-text error-text">{error}</p>}
    </section>
  );
}
