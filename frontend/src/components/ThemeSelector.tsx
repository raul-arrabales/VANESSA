import { useTranslation } from "react-i18next";
import { useTheme } from "../theme/ThemeProvider";

export default function ThemeSelector(): JSX.Element {
  const { t } = useTranslation("common");
  const { theme, themeFamily, themeFamilies, getFamilyPresets, setTheme } = useTheme();

  return (
    <fieldset className="theme-selector card-stack">
      <legend className="field-label">{t("settings.personalization.theme.selectorLabel")}</legend>
      <p className="status-text">{t("settings.personalization.theme.selectorHelp")}</p>
      <div className="theme-family-grid">
        {themeFamilies.map((family) => {
          const presets = getFamilyPresets(family.id);

          return (
            <section
              key={family.id}
              className="theme-family-card"
              data-active={String(themeFamily.id === family.id)}
              aria-label={t(family.titleKey)}
            >
              <div className="card-stack">
                <div className="theme-family-header">
                  <h3 className="section-title">{t(family.titleKey)}</h3>
                  <p className="status-text">{t(family.descriptionKey)}</p>
                </div>
                <div className="theme-preset-list" role="radiogroup" aria-label={t(family.titleKey)}>
                  {presets.map((preset) => (
                    <label
                      key={preset.id}
                      className="theme-preset-option"
                      data-checked={String(theme === preset.id)}
                    >
                      <input
                        type="radio"
                        name="theme-preset"
                        value={preset.id}
                        checked={theme === preset.id}
                        onChange={() => setTheme(preset.id)}
                      />
                      <span className="theme-preset-copy">
                        <span className="theme-preset-title">{t(preset.titleKey)}</span>
                        <span className="theme-preset-description">{t(preset.descriptionKey)}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </section>
          );
        })}
      </div>
    </fieldset>
  );
}
