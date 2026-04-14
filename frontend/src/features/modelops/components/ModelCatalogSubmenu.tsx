import { useTranslation } from "react-i18next";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import type { PageSubmenuItem } from "../../../components/navigation";

type ModelCatalogSubmenuView = "catalog" | "detail" | "test";

type ModelCatalogSubmenuProps = {
  activeView: ModelCatalogSubmenuView;
  modelId?: string;
  modelName?: string;
  showDetailView?: boolean;
  showTestView?: boolean;
};

export default function ModelCatalogSubmenu({
  activeView,
  modelId = "",
  modelName = "",
  showDetailView = false,
  showTestView = false,
}: ModelCatalogSubmenuProps): JSX.Element {
  const { t } = useTranslation("common");
  const displayName = modelName || modelId || t("modelOps.detail.title");
  const encodedModelId = modelId ? encodeURIComponent(modelId) : "";
  const items: PageSubmenuItem[] = [
    {
      id: "catalog",
      label: t("modelOps.catalog.views.catalog"),
      isActive: activeView === "catalog",
      to: "/control/models/catalog",
    },
  ];

  if (showDetailView || activeView === "detail" || activeView === "test") {
    items.push({
      id: "detail",
      label: t("modelOps.catalog.views.modelDetails", { name: displayName }),
      isActive: activeView === "detail",
      to: encodedModelId ? `/control/models/${encodedModelId}` : undefined,
    });
  }

  if (showTestView || activeView === "test") {
    items.push({
      id: "test",
      label: t("modelOps.catalog.views.testModel", { name: displayName }),
      isActive: activeView === "test",
      to: encodedModelId ? `/control/models/${encodedModelId}/test` : undefined,
    });
  }

  return <PageSubmenuBar items={items} ariaLabel={t("modelOps.catalog.views.aria")} />;
}
