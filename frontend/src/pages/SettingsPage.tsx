import { Link, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import ProfileSection from "../components/ProfileSection";

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const location = useLocation();

  const isSettingsHome = location.pathname === "/settings";
  const isAdmin = user?.role === "admin" || user?.role === "superadmin";
  const isSuperadmin = user?.role === "superadmin";

  return (
    <section className="card-stack" aria-label={t("settings.title")}>
      {isSettingsHome && (
        <>
          <ProfileSection titleKey="settings.profile.title" />

          <article className="panel card-stack">
            <h2 className="section-title">{t("settings.user.title")}</h2>
            <p className="status-text">{t("settings.user.description")}</p>
          </article>

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
                <Link to="/settings/design" className="btn btn-secondary">{t("settings.superadmin.styleGuide")}</Link>
              </div>
            </article>
          )}
        </>
      )}
      <Outlet />
    </section>
  );
}
