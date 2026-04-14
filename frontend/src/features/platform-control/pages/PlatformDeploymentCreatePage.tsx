import { useTranslation } from "react-i18next";
import PlatformDeploymentCreatePanel from "../components/PlatformDeploymentCreatePanel";
import PlatformPageLayout from "../components/PlatformPageLayout";

export default function PlatformDeploymentCreatePage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <PlatformPageLayout
      title={t("platformControl.deployments.newTitle")}
      description={t("platformControl.deployments.newDescription")}
    >
      <PlatformDeploymentCreatePanel />
    </PlatformPageLayout>
  );
}
