import { useTranslation } from "react-i18next";
import OptionCardGrid from "../../../components/OptionCardGrid";
import { useAuth } from "../../../auth/AuthProvider";
import { hasRequiredRole } from "../../../auth/roles";
import { controlCardDefinitions } from "../controlItems";
import type { ControlCardSection } from "../types";

const controlSectionOrder: readonly ControlCardSection[] = ["aiOperations", "vanessaPlatform"] as const;

export default function ControlShellPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const currentRole = user?.role ?? "user";
  const displayName = user?.username ?? user?.email ?? t("app.title");

  const visibleItems = controlCardDefinitions
    .filter((item) => hasRequiredRole(currentRole, item.minimumRole))
    .map((item) => ({
      section: item.section,
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      to: item.to,
      icon: item.icon,
    }));

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("control.title", { username: displayName })}</h2>
      <p className="status-text">{t("control.description")}</p>
      <div className="control-sections">
        {controlSectionOrder.map((section) => {
          const sectionItems = visibleItems.filter((item) => item.section === section);
          if (sectionItems.length === 0) {
            return null;
          }

          return (
            <section key={section} className="control-section card-stack" aria-labelledby={`control-section-${section}`}>
              <h3 id={`control-section-${section}`} className="section-title">
                {t(`control.sections.${section}.title`)}
              </h3>
              <OptionCardGrid items={sectionItems} ariaLabel={t(`control.sections.${section}.aria`)} />
            </section>
          );
        })}
      </div>
    </section>
  );
}
