import { type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

const supportedLanguages = ["en", "es"] as const;

export default function LanguageSwitcher(): JSX.Element {
  const { t, i18n } = useTranslation("common");
  const activeLanguage = i18n.resolvedLanguage?.split("-")[0] ?? "en";

  const handleLanguageChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    const nextLanguage = event.target.value;
    void i18n.changeLanguage(nextLanguage);
  };

  return (
    <label className="control-group language-switcher">
      <span className="field-label">{t("language.label")}</span>
      <select className="field-input" value={activeLanguage} onChange={handleLanguageChange}>
        {supportedLanguages.map((language) => (
          <option key={language} value={language}>
            {t(`language.${language}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
