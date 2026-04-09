import type { ComponentProps } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Composer from "./Composer";

type ResizeObserverInstance = {
  callback: ResizeObserverCallback;
  observe: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
};

const resizeObserverInstances: ResizeObserverInstance[] = [];

const originalGetComputedStyle = window.getComputedStyle.bind(window);
const getComputedStyleMock = vi.spyOn(window, "getComputedStyle");

function createComposer(
  overrides: Partial<ComponentProps<typeof Composer>> = {},
): ComponentProps<typeof Composer> {
  return {
    draft: "",
    error: "",
    disabled: false,
    submitLabel: "Send",
    busyLabel: "Streaming...",
    stopLabel: "Stop response",
    isSending: false,
    canStop: false,
    placeholder: "Type your message",
    onDraftChange: vi.fn(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    onHeightChange: vi.fn(),
    ...overrides,
  };
}

describe("Composer", () => {
  beforeEach(() => {
    resizeObserverInstances.length = 0;
    getComputedStyleMock.mockImplementation((element) => {
      const computedStyle = originalGetComputedStyle(element);
      if (element instanceof HTMLTextAreaElement) {
        return {
          ...computedStyle,
          lineHeight: "20px",
          paddingTop: "4px",
          paddingBottom: "4px",
          borderTopWidth: "1px",
          borderBottomWidth: "1px",
          getPropertyValue: computedStyle.getPropertyValue.bind(computedStyle),
        } as CSSStyleDeclaration;
      }
      return computedStyle;
    });

    class ResizeObserverMock {
      public readonly observe = vi.fn();

      public readonly disconnect = vi.fn();

      public constructor(callback: ResizeObserverCallback) {
        resizeObserverInstances.push({
          callback,
          observe: this.observe,
          disconnect: this.disconnect,
        });
      }
    }

    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  });

  afterEach(() => {
    getComputedStyleMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("starts at one row, auto-grows with draft changes, and scrolls internally after five rows", () => {
    let scrollHeight = 30;
    const composer = createComposer({ draft: "Short draft" });
    const { rerender } = render(<Composer {...composer} />);
    const textarea = screen.getByLabelText("Message") as HTMLTextAreaElement;

    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      get: () => scrollHeight,
    });

    rerender(<Composer {...composer} />);
    expect(textarea).toHaveAttribute("rows", "1");
    expect(textarea.style.height).toBe("30px");
    expect(textarea.style.overflowY).toBe("hidden");

    scrollHeight = 140;
    rerender(<Composer {...composer} draft={"Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6"} />);

    expect(textarea.style.height).toBe("110px");
    expect(textarea.style.overflowY).toBe("auto");
  });

  it("submits on Enter, keeps Shift+Enter as a newline, and ignores IME composition", async () => {
    const onSubmit = vi.fn();
    render(<Composer {...createComposer({ draft: "Keyboard send", onSubmit })} />);

    const textarea = screen.getByLabelText("Message");
    await userEvent.type(textarea, "{Enter}");
    expect(onSubmit).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSubmit).toHaveBeenCalledTimes(1);

    const composingEvent = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    Object.defineProperty(composingEvent, "isComposing", { configurable: true, value: true });
    fireEvent(textarea, composingEvent);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("sends in normal mode, cancels in stop mode, and reports height changes", async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const onHeightChange = vi.fn();
    const composer = createComposer({
      draft: "Need a reply",
      onSubmit,
      onCancel,
      onHeightChange,
    });
    const { rerender, container } = render(<Composer {...composer} />);

    const shell = container.querySelector(".chatbot-composer-shell");
    if (!(shell instanceof HTMLDivElement)) {
      throw new Error("Expected composer shell");
    }

    Object.defineProperty(shell, "getBoundingClientRect", {
      configurable: true,
      value: () => ({ height: 124 }),
    });
    resizeObserverInstances[0]?.callback([], {} as ResizeObserver);

    await waitFor(() => expect(onHeightChange).toHaveBeenCalledWith(124));

    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();

    rerender(
      <Composer
        {...composer}
        isSending
        canStop
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Stop response" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
