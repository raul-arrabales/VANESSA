import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

const DEFAULT_BOTTOM_THRESHOLD = 64;

function distanceFromBottom(element: HTMLElement): number {
  return element.scrollHeight - element.scrollTop - element.clientHeight;
}

type UseStickyChatScrollOptions = {
  bottomThreshold?: number;
};

type ScrollToBottomOptions = {
  behavior?: ScrollBehavior;
  force?: boolean;
};

type UseStickyChatScrollResult = {
  threadRef: RefObject<HTMLDivElement>;
  isPinnedToBottom: boolean;
  hasUnreadContentBelow: boolean;
  handleScroll: () => void;
  scrollToBottom: (options?: ScrollToBottomOptions) => void;
  pinToBottomOnNextUpdate: (behavior?: ScrollBehavior) => void;
};

export function useStickyChatScroll(
  watchValue: unknown,
  options: UseStickyChatScrollOptions = {},
): UseStickyChatScrollResult {
  const bottomThreshold = options.bottomThreshold ?? DEFAULT_BOTTOM_THRESHOLD;
  const threadRef = useRef<HTMLDivElement>(null);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const [hasUnreadContentBelow, setHasUnreadContentBelow] = useState(false);
  const isPinnedRef = useRef(true);
  const pendingScrollBehaviorRef = useRef<ScrollBehavior | null>(null);
  const forceScrollOnNextUpdateRef = useRef(false);

  const syncPinnedState = useCallback((): void => {
    const thread = threadRef.current;
    if (!thread) {
      return;
    }

    const nextPinnedState = distanceFromBottom(thread) <= bottomThreshold;
    isPinnedRef.current = nextPinnedState;
    setIsPinnedToBottom(nextPinnedState);
    if (nextPinnedState) {
      setHasUnreadContentBelow(false);
    }
  }, [bottomThreshold]);

  const performScrollToBottom = useCallback((behavior: ScrollBehavior): void => {
    const thread = threadRef.current;
    if (thread) {
      if (typeof thread.scrollTo === "function") {
        thread.scrollTo({ top: thread.scrollHeight, behavior });
      } else {
        thread.scrollTop = thread.scrollHeight;
      }
    }

    isPinnedRef.current = true;
    setIsPinnedToBottom(true);
    setHasUnreadContentBelow(false);
  }, []);

  const scrollToBottom = useCallback((options?: ScrollToBottomOptions): void => {
    const behavior = options?.behavior ?? "smooth";
    if (options?.force) {
      pendingScrollBehaviorRef.current = behavior;
      forceScrollOnNextUpdateRef.current = true;
      isPinnedRef.current = true;
      setIsPinnedToBottom(true);
      setHasUnreadContentBelow(false);
      return;
    }

    performScrollToBottom(behavior);
  }, [performScrollToBottom]);

  const pinToBottomOnNextUpdate = useCallback((behavior: ScrollBehavior = "auto"): void => {
    pendingScrollBehaviorRef.current = behavior;
    forceScrollOnNextUpdateRef.current = true;
    isPinnedRef.current = true;
    setIsPinnedToBottom(true);
    setHasUnreadContentBelow(false);
  }, []);

  useEffect(() => {
    syncPinnedState();
  }, [syncPinnedState]);

  useEffect(() => {
    const behavior = pendingScrollBehaviorRef.current ?? "auto";
    if (forceScrollOnNextUpdateRef.current || isPinnedRef.current) {
      performScrollToBottom(behavior);
    } else {
      setHasUnreadContentBelow(true);
    }

    pendingScrollBehaviorRef.current = null;
    forceScrollOnNextUpdateRef.current = false;
  }, [performScrollToBottom, watchValue]);

  return {
    threadRef,
    isPinnedToBottom,
    hasUnreadContentBelow,
    handleScroll: syncPinnedState,
    scrollToBottom,
    pinToBottomOnNextUpdate,
  };
}
