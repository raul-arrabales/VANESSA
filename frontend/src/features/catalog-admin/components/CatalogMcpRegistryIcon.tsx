export type McpRegistryIconName = "edit" | "enable" | "disable" | "validate" | "delete" | "description" | "test";

export default function CatalogMcpRegistryIcon({ name }: { name: McpRegistryIconName }): JSX.Element {
  if (name === "edit") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M4 17.25V20h2.75L17.81 8.94l-2.75-2.75L4 17.25Zm15.71-10.04a1 1 0 0 0 0-1.42l-1.5-1.5a1 1 0 0 0-1.42 0l-1.02 1.02 2.75 2.75 1.19-1.19Z" />
      </svg>
    );
  }
  if (name === "enable") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M11 3h2v9h-2V3Zm5.42 2.58 1.42 1.42A8 8 0 1 1 6.16 7L7.58 5.58a6 6 0 1 0 8.84 0Z" />
      </svg>
    );
  }
  if (name === "disable") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M11 3h2v8h-2V3Zm7.78 3.81-1.42 1.42A6 6 0 0 1 8.23 16.7L6.8 18.13A8 8 0 0 0 18.78 6.81ZM4.22 4.22 2.81 5.64l3.01 3.01A8 8 0 0 0 5.87 18l-2.46 2.46 1.42 1.41L21.87 4.83l-1.41-1.42-2.62 2.62a8.03 8.03 0 0 0-3.06-1.75v2.11c.56.2 1.08.49 1.55.84L7.26 16.3a5.99 5.99 0 0 1 .02-6.22L4.22 4.22Z" />
      </svg>
    );
  }
  if (name === "validate") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-1.1 13.7-3.6-3.6 1.4-1.4 2.2 2.17 4.78-4.77 1.42 1.42-6.2 6.18Z" />
      </svg>
    );
  }
  if (name === "test") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M8 5v14l11-7L8 5Zm2 3.65L15.25 12 10 15.35v-6.7ZM4 5h2v14H4V5Z" />
      </svg>
    );
  }
  if (name === "delete") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M8 4h8l1 2h4v2H3V6h4l1-2Zm1 6h2v8H9v-8Zm4 0h2v8h-2v-8ZM6 10h12l-1 10H7L6 10Z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 4h16v16H4V4Zm3 4h10V6H7v2Zm0 4h10v-2H7v2Zm0 4h7v-2H7v2Z" />
    </svg>
  );
}
