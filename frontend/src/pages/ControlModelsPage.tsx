import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import ModelAccessPage from "./ModelAccessPage";
import SuperAdminModelsPage from "./SuperAdminModelsPage";

export default function ControlModelsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelsHub.title")}</h2>
        <p className="status-text">
          {isSuperadmin ? t("modelsHub.superadminDescription") : t("modelsHub.description")}
        </p>
      </article>
      <ModelAccessPage />
      {isSuperadmin && <SuperAdminModelsPage />}
    </section>
  );
}
