import { useTranslation } from "react-i18next";
import OptionCardGrid from "../../../components/OptionCardGrid";

export default function PlaygroundsHomePage(): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("playgrounds.title")}</h2>
      <p className="status-text">{t("playgrounds.description")}</p>
      <OptionCardGrid
        ariaLabel={t("playgrounds.aria")}
        items={[
          {
            id: "chat",
            title: t("playgrounds.chat.title"),
            description: t("playgrounds.chat.description"),
            to: "/playgrounds/chat",
            icon: "ai",
          },
          {
            id: "knowledge",
            title: t("playgrounds.knowledge.title"),
            description: t("playgrounds.knowledge.description"),
            to: "/playgrounds/knowledge",
            icon: "ai",
          },
        ]}
      />
    </section>
  );
}
