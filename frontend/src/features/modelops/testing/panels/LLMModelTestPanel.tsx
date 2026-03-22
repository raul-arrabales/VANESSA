import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { LlmModelTestInput, ModelTestPanelRendererProps } from "../types";

export default function LLMModelTestPanel({
  isPending,
  defaultInputs,
  onRun,
}: ModelTestPanelRendererProps<LlmModelTestInput>): JSX.Element {
  const { t } = useTranslation("common");
  const [prompt, setPrompt] = useState(defaultInputs.prompt);

  useEffect(() => {
    setPrompt(defaultInputs.prompt);
  }, [defaultInputs.prompt]);

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.testing.llmTitle")}</h2>
      <label className="field-label" htmlFor="llm-test-prompt">{t("modelOps.testing.promptLabel")}</label>
      <textarea
        id="llm-test-prompt"
        className="field-input"
        rows={5}
        value={prompt}
        onChange={(event) => setPrompt(event.currentTarget.value)}
      />
      <div className="button-row">
        <button
          type="button"
          className="btn btn-primary"
          disabled={isPending || !prompt.trim()}
          onClick={() => void onRun({ prompt: prompt.trim() })}
        >
          {isPending ? t("modelOps.testing.running") : t("modelOps.actions.runTest")}
        </button>
      </div>
    </article>
  );
}
