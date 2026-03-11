import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "../components/LanguageSwitcher";
import ProfileSection from "../components/ProfileSection";
import ThemeToggle from "../components/ThemeToggle";
import RuntimeProfileSection from "../components/RuntimeProfileSection";

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="card-stack" aria-label={t("settings.title")}>
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
            <Link to="/settings/design" className="btn btn-secondary">
              {t("settings.personalization.theme.styleEditor")}
            </Link>
          </div>
        </section>
        <section className="card-stack" aria-label={t("settings.navigation.title")}>
          <h3 className="section-title">{t("settings.navigation.title")}</h3>
          <p className="status-text">{t("settings.navigation.description")}</p>
          <div className="button-row">
            <Link to="/control" className="btn btn-secondary">{t("nav.control")}</Link>
            <Link to="/control/models" className="btn btn-secondary">{t("nav.models")}</Link>
          </div>
        </section>
      </article>
    </section>
  );
}
