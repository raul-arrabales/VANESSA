import { useTranslation } from "react-i18next";
import PlatformPageLayout from "../components/PlatformPageLayout";
import PlatformProviderCreatePanel from "../components/PlatformProviderCreatePanel";

export default function PlatformProviderCreatePage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <PlatformPageLayout
      title={t("platformControl.providers.newTitle")}
      description={t("platformControl.providers.newDescription")}
    >
      <PlatformProviderCreatePanel />
    </PlatformPageLayout>
  );
}
