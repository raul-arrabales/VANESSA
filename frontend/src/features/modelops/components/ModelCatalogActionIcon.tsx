export type ModelCatalogActionIconName = "details" | "test" | "register";

export default function ModelCatalogActionIcon({ name }: { name: ModelCatalogActionIconName }): JSX.Element {
  if (name === "test") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M8 5v14l11-7L8 5Zm2 3.65L15.25 12 10 15.35v-6.7ZM4 5h2v14H4V5Z" />
      </svg>
    );
  }
  if (name === "register") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M11 4h2v7h7v2h-7v7h-2v-7H4v-2h7V4Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 4h16v16H4V4Zm3 4h10V6H7v2Zm0 4h10v-2H7v2Zm0 4h7v-2H7v2Z" />
    </svg>
  );
}
