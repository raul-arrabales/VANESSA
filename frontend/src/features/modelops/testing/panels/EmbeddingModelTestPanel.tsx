import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { EmbeddingModelTestInput, ModelTestPanelRendererProps } from "../types";

export default function EmbeddingModelTestPanel({
  isPending,
  defaultInputs,
  runDisabled = false,
  onRun,
}: ModelTestPanelRendererProps<EmbeddingModelTestInput>): JSX.Element {
  const { t } = useTranslation("common");
  const [text, setText] = useState(defaultInputs.text);

  useEffect(() => {
    setText(defaultInputs.text);
  }, [defaultInputs.text]);

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.testing.embeddingsTitle")}</h2>
      <label className="field-label" htmlFor="embedding-test-input">{t("modelOps.testing.textLabel")}</label>
      <textarea
        id="embedding-test-input"
        className="field-input"
        rows={4}
        value={text}
        onChange={(event) => setText(event.currentTarget.value)}
      />
      <div className="button-row">
        <button
          type="button"
          className="btn btn-primary"
          disabled={isPending || runDisabled || !text.trim()}
          onClick={() => void onRun({ text: text.trim() })}
        >
          {isPending ? t("modelOps.testing.running") : t("modelOps.actions.runTest")}
        </button>
      </div>
    </article>
  );
}
