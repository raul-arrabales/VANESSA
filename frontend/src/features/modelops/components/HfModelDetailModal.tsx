import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { HfModelDetails } from "../../../api/modelops/types";
import {
  HfModelFileFormatsSection,
  HfModelFileListSection,
  HfModelIdentityGrid,
  HfModelMetadataSections,
  HfModelTagsSection,
} from "./HfModelDetailSections";
import {
  getFileFormatSummary,
  getMetadataSections,
} from "./hfModelDetailPresentation";

type HfModelDetailModalProps = {
  model: HfModelDetails;
  onClose: () => void;
};

export default function HfModelDetailModal({
  model,
  onClose,
}: HfModelDetailModalProps): JSX.Element {
  const { t } = useTranslation("common");
  const emptyLabel = t("modelOps.local.hfDetails.unavailable");
  const formatSummary = useMemo(() => getFileFormatSummary(model.files), [model.files]);
  const metadataSections = getMetadataSections(model, {
    cardData: t("modelOps.local.hfDetails.cardData"),
    config: t("modelOps.local.hfDetails.config"),
    safetensors: t("modelOps.local.hfDetails.safetensors"),
    modelIndex: t("modelOps.local.hfDetails.modelIndex"),
    transformersInfo: t("modelOps.local.hfDetails.transformersInfo"),
  });

  return (
    <ModalDialog
      className="modelops-hf-detail-modal"
      eyebrow={t("modelOps.local.hfDetails.eyebrow")}
      title={model.source_id}
      description={t("modelOps.local.hfDetails.description")}
      onClose={onClose}
      actions={(
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          {t("actionFeedback.dialog.close")}
        </button>
      )}
    >
      <div className="card-stack">
        <HfModelIdentityGrid model={model} emptyLabel={emptyLabel} t={t} />
        <HfModelTagsSection tags={model.tags} emptyLabel={emptyLabel} t={t} />
        <HfModelFileFormatsSection formatSummary={formatSummary} emptyLabel={emptyLabel} t={t} />
        <HfModelFileListSection files={model.files} emptyLabel={emptyLabel} t={t} />
        <HfModelMetadataSections metadataSections={metadataSections} t={t} />
      </div>
    </ModalDialog>
  );
}
