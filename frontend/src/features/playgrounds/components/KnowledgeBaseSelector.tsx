import { useTranslation } from "react-i18next";
import type { Ref } from "react";
import type { PlaygroundKnowledgeBaseOption } from "../../../api/playgrounds";

type KnowledgeBaseSelectorProps = {
  knowledgeBases: PlaygroundKnowledgeBaseOption[];
  value: string;
  disabled: boolean;
  isLoading: boolean;
  selectRef?: Ref<HTMLSelectElement>;
  onChange: (value: string) => void;
};

export default function KnowledgeBaseSelector({
  knowledgeBases,
  value,
  disabled,
  isLoading,
  selectRef,
  onChange,
}: KnowledgeBaseSelectorProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <>
      <label className="field-label" htmlFor="knowledge-base-picker">
        {t("playgrounds.shared.knowledgeBaseSelector.label")}
      </label>
      <select
        ref={selectRef}
        id="knowledge-base-picker"
        aria-label={t("playgrounds.shared.knowledgeBaseSelector.aria")}
        className="field-input"
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        disabled={disabled}
      >
        <option value="">
          {isLoading
            ? t("playgrounds.shared.knowledgeBaseSelector.loading")
            : t("playgrounds.shared.knowledgeBaseSelector.placeholder")}
        </option>
        {knowledgeBases.map((knowledgeBase) => (
          <option key={knowledgeBase.id} value={knowledgeBase.id}>{knowledgeBase.display_name}</option>
        ))}
      </select>
    </>
  );
}
