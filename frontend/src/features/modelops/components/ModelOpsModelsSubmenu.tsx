import { useTranslation } from "react-i18next";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import type { PageSubmenuItem } from "../../../components/navigation";

type ModelOpsModelsSubmenuView = "summary" | "catalog" | "detail" | "test";

type ModelOpsModelsSubmenuProps = {
  activeView: ModelOpsModelsSubmenuView;
  modelId?: string;
  modelName?: string;
  showDetailView?: boolean;
  showTestView?: boolean;
};

export default function ModelOpsModelsSubmenu({
  activeView,
  modelId = "",
  modelName = "",
  showDetailView = false,
  showTestView = false,
}: ModelOpsModelsSubmenuProps): JSX.Element {
  const { t } = useTranslation("common");
  const displayName = modelName || modelId || t("modelOps.detail.title");
  const encodedModelId = modelId ? encodeURIComponent(modelId) : "";
  const items: PageSubmenuItem[] = [
    {
      id: "summary",
      label: t("modelOps.models.views.summary"),
      isActive: activeView === "summary",
      to: "/control/models",
    },
    {
      id: "catalog",
      label: t("modelOps.models.views.catalog"),
      isActive: activeView === "catalog",
      to: "/control/models/catalog",
    },
  ];

  if (showDetailView || activeView === "detail" || activeView === "test") {
    items.push({
      id: "detail",
      label: t("modelOps.models.views.modelDetails", { name: displayName }),
      isActive: activeView === "detail",
      to: encodedModelId ? `/control/models/${encodedModelId}` : undefined,
    });
  }

  if (showTestView || activeView === "test") {
    items.push({
      id: "test",
      label: t("modelOps.models.views.testModel", { name: displayName }),
      isActive: activeView === "test",
      to: encodedModelId ? `/control/models/${encodedModelId}/test` : undefined,
    });
  }

  return <PageSubmenuBar items={items} ariaLabel={t("modelOps.models.views.aria")} />;
}
