import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

type EmbeddingModelTestPanelProps = {
  isPending: boolean;
  onRun: (inputs: { text: string }) => Promise<void>;
};

export default function EmbeddingModelTestPanel({
  isPending,
  onRun,
}: EmbeddingModelTestPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const [text, setText] = useState("hello world");

  useEffect(() => {
    setText("hello world");
  }, []);

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
          disabled={isPending || !text.trim()}
          onClick={() => void onRun({ text: text.trim() })}
        >
          {isPending ? t("modelOps.testing.running") : t("modelOps.actions.runTest")}
        </button>
      </div>
    </article>
  );
}
