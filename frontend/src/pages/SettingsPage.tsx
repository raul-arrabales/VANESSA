import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import ProfileSection from "../components/ProfileSection";

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();

  const isAdmin = user?.role === "admin" || user?.role === "superadmin";
  const isSuperadmin = user?.role === "superadmin";

  return (
    <section className="card-stack" aria-label={t("settings.title")}>
      <ProfileSection titleKey="settings.profile.title" />

      {isAdmin && (
        <article className="panel card-stack">
          <h2 className="section-title">{t("settings.admin.title")}</h2>
          <p className="status-text">{t("settings.admin.description")}</p>
          <div className="button-row">
            <Link to="/admin/approvals" className="btn btn-secondary">{t("settings.admin.approvals")}</Link>
          </div>
        </article>
      )}

      {isSuperadmin && (
        <article className="panel card-stack">
          <h2 className="section-title">{t("settings.superadmin.title")}</h2>
          <p className="status-text">{t("settings.superadmin.description")}</p>
          <div className="button-row">
            <Link to="/style-guide" className="btn btn-secondary">{t("settings.superadmin.styleGuide")}</Link>
          </div>
        </article>
      )}
    </section>
  );
}
