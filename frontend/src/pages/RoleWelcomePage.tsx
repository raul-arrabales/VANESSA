import { useTranslation } from "react-i18next";

type RoleWelcomePageProps = {
  role: "user" | "admin" | "superadmin";
};

export default function RoleWelcomePage({ role }: RoleWelcomePageProps): JSX.Element {
  const { t } = useTranslation("common");

  const roleKey = `auth.welcome.${role}`;
  const itemKeys = ["item1", "item2", "item3"] as const;

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t(`${roleKey}.title`)}</h2>
      <p className="status-text">{t(`${roleKey}.subtitle`)}</p>
      <p className="field-label">{t("auth.welcome.availableItems")}</p>
      <ul className="card-stack">
        {itemKeys.map((item) => (
          <li key={item} className="status-text">{t(`${roleKey}.items.${item}`)}</li>
        ))}
      </ul>
    </section>
  );
}
