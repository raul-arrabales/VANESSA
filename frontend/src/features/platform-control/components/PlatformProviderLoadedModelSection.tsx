import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops/types";
import type { PlatformProvider } from "../../../api/platform";
import type { ProviderLoadDisplayData } from "../providerLoad";

type PlatformProviderLoadedModelSectionProps = {
  loadDisplay: ProviderLoadDisplayData;
  onAssignLoadedModel: () => void;
  onClearLoadedModel: () => void;
  onSlotModelChange: (value: string) => void;
  provider: PlatformProvider;
  slotLoading: boolean;
  slotModelId: string;
  slotModels: ManagedModel[];
};

export default function PlatformProviderLoadedModelSection({
  loadDisplay,
  onAssignLoadedModel,
  onClearLoadedModel,
  onSlotModelChange,
  provider,
  slotLoading,
  slotModelId,
  slotModels,
}: PlatformProviderLoadedModelSectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("platformControl.providers.loadedModelTitle")}</h3>
        <p className="status-text">{t("platformControl.providers.loadedModelDescription")}</p>
      </div>
      <div className="platform-detail-grid">
        <div className="platform-summary-card">
          <span className="field-label">{t("platformControl.providers.loadedModelLabel")}</span>
          <strong>{loadDisplay.loadedModelPrimary}</strong>
          {loadDisplay.loadedModelSecondaryDetail ? (
            <span className="status-text">{loadDisplay.loadedModelSecondaryDetail}</span>
          ) : null}
        </div>
        <div className="platform-summary-card">
          <span className="field-label">{t("platformControl.providers.loadedModelStateLabel")}</span>
          <strong>{loadDisplay.providerLoadState}</strong>
          <span className={loadDisplay.hasLoadError ? "status-text error-text" : "status-text"}>
            {loadDisplay.loadStateHelperText}
          </span>
        </div>
      </div>
      <label className="field-label" htmlFor="provider-loaded-model">
        {t("platformControl.providers.loadedModelSelectLabel")}
      </label>
      <select
        id="provider-loaded-model"
        className="field-input"
        value={slotModelId}
        disabled={slotLoading}
        onChange={(event) => onSlotModelChange(event.currentTarget.value)}
      >
        <option value="">{t("platformControl.providers.loadedModelPlaceholder")}</option>
        {slotModels.map((model) => (
          <option key={model.id} value={model.id}>
            {model.name} ({model.id})
          </option>
        ))}
      </select>
      <p className="status-text">
        {t("platformControl.providers.loadedModelHelp", { name: provider.display_name })}
      </p>
      <div className="button-row">
        <button type="button" className="btn btn-primary" disabled={!slotModelId} onClick={onAssignLoadedModel}>
          {t("platformControl.actions.assignLoadedModel")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onClearLoadedModel}>
          {t("platformControl.actions.clearLoadedModel")}
        </button>
      </div>
    </article>
  );
}
