import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatMessageBody from "./ChatMessageBody";

describe("ChatMessageBody", () => {
  it("renders safe markdown with links, tables, and inline formatting", async () => {
    render(
      <ChatMessageBody
        content={"# Title\n\nA **bold** line with [OpenAI](https://openai.com).\n\n| A | B |\n| - | - |\n| 1 | 2 |"}
        renderMarkdown
      />,
    );

    expect(await screen.findByRole("heading", { name: "Title" }, { timeout: 4000 })).toBeVisible();
    expect(screen.getByText("bold", { selector: "strong" })).toBeVisible();
    const link = screen.getByRole("link", { name: "OpenAI" });
    expect(link).toHaveAttribute("href", "https://openai.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer noopener");
    expect(screen.getByRole("table")).toBeVisible();
  });

  it("uses syntax highlighting for fenced code blocks and strips raw html", async () => {
    const { container } = render(
      <ChatMessageBody
        content={"```js\nconst value = 1;\n```\n\n<script>alert('xss')</script>"}
        renderMarkdown
      />,
    );

    await waitFor(() => {
      expect(container.querySelector(".chatbot-code-block code")?.textContent).toContain("const value = 1;");
    });
    expect(container.querySelector(".chatbot-code-block")).not.toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.queryByText("alert('xss')")).toBeNull();
  });

  it("keeps non-markdown user text literal", () => {
    const { container } = render(
      <ChatMessageBody
        content={"**not bold** <em>not html</em>"}
        renderMarkdown={false}
      />,
    );

    expect(screen.getByText("**not bold** <em>not html</em>")).toBeVisible();
    expect(container.querySelector("strong")).toBeNull();
    expect(container.querySelector("em")).toBeNull();
  });
});
