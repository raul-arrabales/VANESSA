import { useTranslation } from "react-i18next";
import OptionCardGrid from "../components/OptionCardGrid";

export default function AiPage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("ai.title")}</h2>
      <p className="status-text">{t("ai.description")}</p>
      <OptionCardGrid
        ariaLabel={t("ai.aria")}
        items={[
          {
            id: "chat",
            title: t("ai.chat.title"),
            description: t("ai.chat.description"),
            to: "/ai/chat",
            icon: "ai",
          },
        ]}
      />
    </section>
  );
}
