import { useEffect, useLayoutEffect, useRef } from "react";
import type { KeyboardEvent } from "react";

const DEFAULT_COMPOSER_LINE_HEIGHT = 24;
const DEFAULT_MAX_VISIBLE_ROWS = 5;

type UseAutoResizingComposerOptions = {
  draft: string;
  disabled: boolean;
  isSending: boolean;
  canStop: boolean;
  onSubmit: () => void;
  onCancel: () => void;
  onHeightChange?: (height: number) => void;
  defaultLineHeight?: number;
  maxVisibleRows?: number;
};

type UseAutoResizingComposerResult = {
  shellRef: React.RefObject<HTMLDivElement>;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
  handleKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  handleActionClick: () => void;
  isActionDisabled: boolean;
  isTextareaDisabled: boolean;
};

export function useAutoResizingComposer({
  draft,
  disabled,
  isSending,
  canStop,
  onSubmit,
  onCancel,
  onHeightChange,
  defaultLineHeight = DEFAULT_COMPOSER_LINE_HEIGHT,
  maxVisibleRows = DEFAULT_MAX_VISIBLE_ROWS,
}: UseAutoResizingComposerOptions): UseAutoResizingComposerResult {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";

    const computedStyle = window.getComputedStyle(textarea);
    const lineHeight = Number.parseFloat(computedStyle.lineHeight) || defaultLineHeight;
    const paddingBlock = (Number.parseFloat(computedStyle.paddingTop) || 0)
      + (Number.parseFloat(computedStyle.paddingBottom) || 0);
    const borderBlock = (Number.parseFloat(computedStyle.borderTopWidth) || 0)
      + (Number.parseFloat(computedStyle.borderBottomWidth) || 0);
    const maxHeight = (lineHeight * maxVisibleRows) + paddingBlock + borderBlock;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);

    textarea.style.height = `${Math.max(nextHeight, lineHeight + paddingBlock + borderBlock)}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [defaultLineHeight, draft, maxVisibleRows]);

  useEffect(() => {
    const reportHeight = (): void => {
      const shell = shellRef.current;
      if (shell) {
        onHeightChange?.(Math.ceil(shell.getBoundingClientRect().height));
      }
    };

    reportHeight();

    if (typeof ResizeObserver !== "function" || !shellRef.current) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => {
      reportHeight();
    });
    resizeObserver.observe(shellRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [disabled, draft, isSending, onHeightChange]);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (
      event.key === "Enter"
      && !event.shiftKey
      && !event.nativeEvent.isComposing
      && !disabled
      && !isSending
      && draft.trim()
    ) {
      event.preventDefault();
      onSubmit();
    }
  };

  const handleActionClick = (): void => {
    if (canStop) {
      onCancel();
      return;
    }
    onSubmit();
  };

  return {
    shellRef,
    textareaRef,
    handleKeyDown,
    handleActionClick,
    isActionDisabled: isSending ? !canStop : (disabled || !draft.trim()),
    isTextareaDisabled: disabled || isSending,
  };
}
