type ModelStatusBadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "warning" | "info" | "danger";
};

export default function ModelStatusBadge({ label, tone = "neutral" }: ModelStatusBadgeProps): JSX.Element {
  return <span className={`status-chip status-chip-${tone}`}>{label}</span>;
}
