import OptionCardGrid, { type OptionCardItem } from "../../../components/OptionCardGrid";

type ModelOpsEntryCardsProps = {
  items: OptionCardItem[];
  ariaLabel: string;
};

export default function ModelOpsEntryCards({ items, ariaLabel }: ModelOpsEntryCardsProps): JSX.Element {
  return <OptionCardGrid items={items} ariaLabel={ariaLabel} />;
}
