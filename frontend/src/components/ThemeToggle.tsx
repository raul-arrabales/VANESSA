import { useTranslation } from "react-i18next";
import { useTheme } from "../theme/ThemeProvider";

export default function ThemeToggle(): JSX.Element {
  const { t } = useTranslation("common");
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      className="btn btn-ghost"
      onClick={toggleTheme}
      aria-label={t("theme.toggle.aria")}
      title={t("theme.toggle.aria")}
      data-testid="theme-toggle"
    >
      {theme === "light" ? t("theme.toggle.toDark") : t("theme.toggle.toLight")}
    </button>
  );
}
