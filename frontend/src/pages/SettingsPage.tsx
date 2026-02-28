import { Link, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import LanguageSwitcher from "../components/LanguageSwitcher";
import ProfileSection from "../components/ProfileSection";
import ThemeToggle from "../components/ThemeToggle";
import RuntimeProfileSection from "../components/RuntimeProfileSection";

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const location = useLocation();

  const isSettingsHome = location.pathname === "/settings";
  const isSuperadmin = user?.role === "superadmin";

  return (
    <section className="card-stack" aria-label={t("settings.title")}>
      {isSettingsHome && (
        <>
          <ProfileSection titleKey="settings.profile.title" />
          <article className="panel card-stack">
            <h2 className="section-title">{t("settings.personalization.title")}</h2>
            <p className="status-text">{t("settings.personalization.description")}</p>
            <section className="card-stack" aria-label={t("settings.personalization.language.title")}>
              <h3 className="section-title">{t("settings.personalization.language.title")}</h3>
              <p className="status-text">{t("settings.personalization.language.description")}</p>
              <LanguageSwitcher />
            </section>
            <RuntimeProfileSection />
            <section className="card-stack" aria-label={t("settings.personalization.theme.title")}>
              <h3 className="section-title">{t("settings.personalization.theme.title")}</h3>
              <p className="status-text">{t("settings.personalization.theme.description")}</p>
              <div className="button-row">
                <ThemeToggle />
                {isSuperadmin && (
                  <Link to="/settings/design" className="btn btn-secondary">
                    {t("settings.personalization.theme.styleEditor")}
                  </Link>
                )}
              </div>
            </section>
            <section className="card-stack" aria-label="Model access settings">
              <h3 className="section-title">Model access</h3>
              <p className="status-text">Manage your provider credentials and register models available to your account.</p>
              <div className="button-row">
                <Link to="/settings/model-access" className="btn btn-secondary">Open model access</Link>
              </div>
            </section>
          </article>
        </>
      )}
      <Outlet />
    </section>
  );
}
