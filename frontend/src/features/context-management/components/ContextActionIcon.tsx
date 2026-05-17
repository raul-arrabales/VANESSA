export type ContextActionIconName = "edit" | "delete" | "sync" | "metadata" | "open";

export default function ContextActionIcon({ name }: { name: ContextActionIconName }): JSX.Element {
  if (name === "edit") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M4 17.25V20h2.75L17.81 8.94l-2.75-2.75L4 17.25Zm15.71-10.04a1 1 0 0 0 0-1.42l-1.5-1.5a1 1 0 0 0-1.42 0l-1.02 1.02 2.75 2.75 1.19-1.19Z" />
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
  if (name === "sync") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M17.65 6.35A8 8 0 0 0 4.08 10H2l3 3 3-3H6.13a6 6 0 0 1 10.11-2.24L17.65 6.35ZM22 14l-3-3-3 3h1.87a6 6 0 0 1-10.11 2.24l-1.41 1.41A8 8 0 0 0 19.92 14H22Z" />
      </svg>
    );
  }
  if (name === "open") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M5 5h7v2H7v10h10v-5h2v7H5V5Zm9 0h5v5h-2V8.41l-6.3 6.3-1.4-1.42 6.29-6.29H14V5Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 4h16v16H4V4Zm3 4h10V6H7v2Zm0 4h10v-2H7v2Zm0 4h7v-2H7v2Z" />
    </svg>
  );
}
