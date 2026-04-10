import { useTranslation } from "react-i18next";
import type { KnowledgeBaseSchemaProperty } from "../../../api/context";
import { KnowledgeBaseMetadataEditor } from "./KnowledgeBaseMetadataEditor";
import type { MetadataEntryFormState } from "../types";

type Props = {
  schemaProperties: KnowledgeBaseSchemaProperty[];
  entries: MetadataEntryFormState[];
  onChange: (entries: MetadataEntryFormState[]) => void;
};

export function KnowledgeBaseRetrievalFiltersEditor({
  schemaProperties,
  entries,
  onChange,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <KnowledgeBaseMetadataEditor
      schemaProperties={schemaProperties}
      entries={entries}
      onChange={onChange}
      copy={{
        title: t("contextManagement.retrievalFilters.title"),
        description: t("contextManagement.retrievalFilters.description"),
        empty: t("contextManagement.retrievalFilters.empty"),
        noSchemaProperties: t("contextManagement.retrievalFilters.noSchemaProperties"),
        add: t("contextManagement.retrievalFilters.add"),
        remove: t("contextManagement.retrievalFilters.remove"),
      }}
    />
  );
}
