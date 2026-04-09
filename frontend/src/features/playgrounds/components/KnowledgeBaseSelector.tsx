import { useTranslation } from "react-i18next";
import type { PlaygroundKnowledgeBaseOption } from "../../../api/playgrounds";

type KnowledgeBaseSelectorProps = {
  knowledgeBases: PlaygroundKnowledgeBaseOption[];
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
};

export default function KnowledgeBaseSelector({
  knowledgeBases,
  value,
  disabled,
  onChange,
}: KnowledgeBaseSelectorProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <label>
      {t("playgrounds.shared.knowledgeBaseSelector.label")}
      <select
        aria-label={t("playgrounds.shared.knowledgeBaseSelector.aria")}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        disabled={disabled}
      >
        <option value="">{t("playgrounds.shared.knowledgeBaseSelector.placeholder")}</option>
        {knowledgeBases.map((knowledgeBase) => (
          <option key={knowledgeBase.id} value={knowledgeBase.id}>{knowledgeBase.display_name}</option>
        ))}
      </select>
    </label>
  );
}
