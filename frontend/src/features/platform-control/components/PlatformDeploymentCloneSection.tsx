import { useTranslation } from "react-i18next";
import type { DeploymentCloneFormState } from "../deploymentEditor";

type PlatformDeploymentCloneSectionProps = {
  cloneForm: DeploymentCloneFormState;
  cloning: boolean;
  onClone: () => void;
  onCloneFormChange: (nextValue: DeploymentCloneFormState) => void;
};

export default function PlatformDeploymentCloneSection({
  cloneForm,
  cloning,
  onClone,
  onCloneFormChange,
}: PlatformDeploymentCloneSectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("platformControl.sections.clone")}</h3>
        <p className="status-text">{t("platformControl.deployments.cloneDescription")}</p>
      </div>
      <form
        className="card-stack"
        onSubmit={(event) => {
          event.preventDefault();
          onClone();
        }}
      >
        <div className="form-grid">
          <label className="card-stack">
            <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
            <input
              className="field-input"
              value={cloneForm.slug}
              onChange={(event) => onCloneFormChange({ ...cloneForm, slug: event.target.value })}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
            <input
              className="field-input"
              value={cloneForm.displayName}
              onChange={(event) => onCloneFormChange({ ...cloneForm, displayName: event.target.value })}
            />
          </label>
        </div>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
          <textarea
            className="field-input form-textarea"
            value={cloneForm.description}
            onChange={(event) => onCloneFormChange({ ...cloneForm, description: event.target.value })}
          />
        </label>
        <div className="platform-action-row">
          <span className="status-text">{t("platformControl.deployments.cloning", { slug: cloneForm.slug })}</span>
          <button type="submit" className="btn btn-primary" disabled={cloning}>
            {cloning ? t("platformControl.actions.saving") : t("platformControl.actions.cloneDeployment")}
          </button>
        </div>
      </form>
    </article>
  );
}
