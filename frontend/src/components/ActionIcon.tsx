export type ActionIconName =
  | "delete"
  | "deployment"
  | "description"
  | "details"
  | "disable"
  | "edit"
  | "enable"
  | "collapse"
  | "expand"
  | "lifecycle"
  | "metadata"
  | "open"
  | "register"
  | "sync"
  | "test"
  | "validate";

export default function ActionIcon({ name }: { name: ActionIconName }): JSX.Element {
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
  if (name === "deployment") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M4 6.5 12 3l8 3.5v4L12 14 4 10.5v-4Zm2 1.31v1.39l6 2.62 6-2.62V7.81L12 10.44 6 7.81ZM4 13.5 12 17l8-3.5v4L12 21l-8-3.5v-4Zm2 1.31v1.39l6 2.62 6-2.62v-1.39L12 17.44l-6-2.63Z" />
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
  if (name === "expand") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="m7.4 8.6 4.6 4.6 4.6-4.6L18 10l-6 6-6-6 1.4-1.4Z" />
      </svg>
    );
  }
  if (name === "collapse") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M7.4 15.4 6 14l6-6 6 6-1.4 1.4-4.6-4.6-4.6 4.6Z" />
      </svg>
    );
  }
  if (name === "lifecycle") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M6 5a3 3 0 1 1 2.83 4H8v2h8V9h-.83A3 3 0 1 1 18 11v4a3 3 0 1 1-2.83 4h-6.34A3 3 0 1 1 6 15v-4a2 2 0 0 1 2-2h1V7H8.83A3 3 0 0 1 6 5Zm0-1a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm12 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2ZM6 17a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm12 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 4h16v16H4V4Zm3 4h10V6H7v2Zm0 4h10v-2H7v2Zm0 4h7v-2H7v2Z" />
    </svg>
  );
}
