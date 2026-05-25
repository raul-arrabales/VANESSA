import { useEffect, useMemo, useState } from "react";
import type { CatalogExecutionTraceEntry } from "../../../api/catalogExecutionTrace";
import { progressIndexFromTrace } from "../catalogExecutionTrace";

function activeStageIndexFromElapsed(elapsedMs: number, stageCount: number): number {
  if (stageCount <= 1) {
    return 0;
  }
  if (elapsedMs < 800) {
    return 0;
  }
  if (elapsedMs < 1800) {
    return Math.min(1, stageCount - 1);
  }
  if (elapsedMs < 3600) {
    return Math.min(2, stageCount - 1);
  }
  return stageCount - 1;
}

type UseCatalogToolTestProgressOptions = {
  testing: boolean;
  traceEntries: CatalogExecutionTraceEntry[];
  stageCount: number;
};

export function useCatalogToolTestProgress({
  testing,
  traceEntries,
  stageCount,
}: UseCatalogToolTestProgressOptions) {
  const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (testing) {
      setStartedAt((current) => current ?? Date.now());
      setIsProgressModalOpen(true);
      return;
    }
    setStartedAt(null);
    setElapsedMs(0);
    setIsProgressModalOpen(false);
  }, [testing]);

  useEffect(() => {
    if (!testing || startedAt === null) {
      return;
    }
    setElapsedMs(Math.max(0, Date.now() - startedAt));
    const intervalId = window.setInterval(() => {
      setElapsedMs(Math.max(0, Date.now() - startedAt));
    }, 150);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [startedAt, testing]);

  const activeStageIndex = useMemo(() => {
    const traceIndex = progressIndexFromTrace(traceEntries);
    if (traceIndex !== null) {
      return Math.min(traceIndex, Math.max(0, stageCount - 1));
    }
    return activeStageIndexFromElapsed(elapsedMs, stageCount);
  }, [elapsedMs, stageCount, traceEntries]);

  const progressPercent = stageCount > 1
    ? Math.round((activeStageIndex / (stageCount - 1)) * 100)
    : 100;

  return {
    activeStageIndex,
    elapsedMs,
    isProgressModalOpen,
    progressPercent,
    dismissProgressModal: () => setIsProgressModalOpen(false),
    openProgressModal: () => setIsProgressModalOpen(true),
  };
}
