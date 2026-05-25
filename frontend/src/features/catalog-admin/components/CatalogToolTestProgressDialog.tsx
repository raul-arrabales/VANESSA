import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { CatalogTool } from "../../../api/catalog";
import { catalogToolBackendLabelKey } from "../catalogToolBackends";

export type CatalogToolTestProgressStage = {
  id: string;
  label: string;
  detail: string;
};

type CatalogToolTestProgressDialogProps = {
  tool: CatalogTool;
  elapsedMs: number;
  activeStageIndex: number;
  progressPercent: number;
  onDismiss: () => void;
};

function buildToolTestStages(
  tool: CatalogTool,
  t: (key: string, options?: Record<string, unknown>) => string,
): CatalogToolTestProgressStage[] {
  const backend = tool.spec.execution_backend;
  const runtimeLabel = backend
    ? t(`catalogControl.executionBackend.${catalogToolBackendLabelKey(backend)}`)
    : t("catalogControl.tools.progress.runtimeFallback");
  return [
    {
      id: "queued",
      label: t("catalogControl.tools.progress.queuedLabel"),
      detail: t("catalogControl.tools.progress.queuedDetail", { name: tool.spec.name }),
    },
    {
      id: "validated",
      label: t("catalogControl.tools.progress.validatedLabel"),
      detail: t("catalogControl.tools.progress.validatedDetail"),
    },
    {
      id: "runtime",
      label: t("catalogControl.tools.progress.runtimeLabel"),
      detail: t("catalogControl.tools.progress.runtimeDetail", { runtime: runtimeLabel }),
    },
    {
      id: "waiting",
      label: t("catalogControl.tools.progress.waitingLabel"),
      detail: t("catalogControl.tools.progress.waitingDetail"),
    },
  ];
}

export function catalogToolTestProgressStageCount(): number {
  return 4;
}

export default function CatalogToolTestProgressDialog({
  tool,
  elapsedMs,
  activeStageIndex,
  progressPercent,
  onDismiss,
}: CatalogToolTestProgressDialogProps): JSX.Element {
  const { t } = useTranslation("common");
  const stages = useMemo(() => buildToolTestStages(tool, t), [tool, t]);

  return (
    <ModalDialog
      className="catalog-tool-test-progress-modal"
      title={t("catalogControl.tools.progress.title", { name: tool.spec.name })}
      description={t("catalogControl.tools.progress.description")}
      onClose={onDismiss}
      actions={(
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onDismiss}
        >
          {t("catalogControl.tools.progress.exit")}
        </button>
      )}
    >
      <div className="catalog-tool-test-progress">
        <div className="catalog-tool-test-progress-hero" aria-hidden="true">
          <span className="catalog-tool-test-progress-orbit" />
          <span className="catalog-tool-test-progress-core" />
        </div>
        <div className="catalog-tool-test-progress-meter" aria-label={t("catalogControl.tools.progress.barLabel")}>
          <div className="catalog-tool-test-progress-meter-track">
            <div
              className="catalog-tool-test-progress-meter-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="catalog-tool-test-progress-meter-text">
            {t("catalogControl.tools.progress.elapsed", { seconds: (elapsedMs / 1000).toFixed(1) })}
          </span>
        </div>
        <ol className="catalog-tool-test-progress-stage-list">
          {stages.map((stage, index) => {
            const state = index < activeStageIndex ? "done" : index === activeStageIndex ? "active" : "pending";
            return (
              <li key={stage.id} className="catalog-tool-test-progress-stage" data-state={state}>
                <span className="catalog-tool-test-progress-stage-icon" aria-hidden="true" />
                <div className="card-stack">
                  <strong>{stage.label}</strong>
                  <span className="status-text">{stage.detail}</span>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </ModalDialog>
  );
}
