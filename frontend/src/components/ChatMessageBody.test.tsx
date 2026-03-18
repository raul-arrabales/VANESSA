import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatMessageBody from "./ChatMessageBody";

describe("ChatMessageBody", () => {
  it("renders safe markdown with links, tables, and inline formatting", () => {
    render(
      <ChatMessageBody
        content={"# Title\n\nA **bold** line with [OpenAI](https://openai.com).\n\n| A | B |\n| - | - |\n| 1 | 2 |"}
        renderMarkdown
      />,
    );

    expect(screen.getByRole("heading", { name: "Title" })).toBeVisible();
    expect(screen.getByText("bold", { selector: "strong" })).toBeVisible();
    const link = screen.getByRole("link", { name: "OpenAI" });
    expect(link).toHaveAttribute("href", "https://openai.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer noopener");
    expect(screen.getByRole("table")).toBeVisible();
  });

  it("uses syntax highlighting for fenced code blocks and strips raw html", () => {
    const { container } = render(
      <ChatMessageBody
        content={"```js\nconst value = 1;\n```\n\n<script>alert('xss')</script>"}
        renderMarkdown
      />,
    );

    expect(container.querySelector(".chatbot-code-block")).not.toBeNull();
    expect(screen.getByText("const")).toBeVisible();
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
