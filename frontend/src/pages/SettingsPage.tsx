import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "../components/LanguageSwitcher";
import ProfileSection from "../components/ProfileSection";
import ThemeSelector from "../components/ThemeSelector";

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="card-stack" aria-label={t("settings.title")}>
      <ProfileSection titleKey="settings.profile.title" />

      <article className="panel card-stack">
        <h2 className="section-title">{t("settings.personalization.language.title")}</h2>
        <p className="status-text">{t("settings.personalization.language.description")}</p>
        <LanguageSwitcher />
      </article>

      <article className="panel card-stack">
        <h2 className="section-title">{t("settings.personalization.theme.title")}</h2>
        <p className="status-text">{t("settings.personalization.theme.description")}</p>
        <ThemeSelector />
        <div className="button-row">
          <Link to="/settings/design" className="btn btn-secondary">
            {t("settings.personalization.theme.styleEditor")}
          </Link>
        </div>
      </article>
    </section>
  );
}
