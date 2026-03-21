type ModelSummaryCard = {
  label: string;
  value: number | string;
};

type ModelSummaryCardsProps = {
  items: ModelSummaryCard[];
};

export default function ModelSummaryCards({ items }: ModelSummaryCardsProps): JSX.Element {
  return (
    <div className="modelops-summary-grid">
      {items.map((item) => (
        <article key={item.label} className="modelops-summary-card">
          <span className="field-label">{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </div>
  );
}
