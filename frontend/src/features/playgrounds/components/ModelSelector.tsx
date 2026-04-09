import { useTranslation } from "react-i18next";

type ModelSelectorProps = {
  models: Array<{ id: string; displayName: string }>;
  value: string;
  isLoading: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
};

export default function ModelSelector({
  models,
  value,
  isLoading,
  disabled,
  onChange,
}: ModelSelectorProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <>
      <label className="field-label" htmlFor="model-picker">{t("playgrounds.shared.modelSelector.label")}</label>
      <select
        id="model-picker"
        aria-label={t("playgrounds.shared.modelSelector.aria")}
        className="field-input"
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        disabled={disabled}
      >
        {models.length === 0 ? (
          <option value="">
            {isLoading ? t("playgrounds.shared.modelSelector.loading") : t("playgrounds.shared.modelSelector.empty")}
          </option>
        ) : null}
        {models.map((model) => (
          <option key={model.id} value={model.id}>{model.displayName}</option>
        ))}
      </select>
    </>
  );
}
