import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { CatalogMcpServer } from "../../../api/catalog";

type CatalogMcpDescriptionModalProps = {
  server: CatalogMcpServer;
  onClose: () => void;
};

export default function CatalogMcpDescriptionModal({
  server,
  onClose,
}: CatalogMcpDescriptionModalProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <ModalDialog
      title={t("catalogControl.mcp.descriptionDialog.title", { name: server.spec.name })}
      description={t("catalogControl.mcp.descriptionDialog.description")}
      className="catalog-description-modal"
      onClose={onClose}
      actions={(
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          {t("catalogControl.mcp.descriptionDialog.close")}
        </button>
      )}
    >
      <div className="catalog-description-modal-body" tabIndex={0}>
        <p>{server.spec.description}</p>
      </div>
    </ModalDialog>
  );
}
