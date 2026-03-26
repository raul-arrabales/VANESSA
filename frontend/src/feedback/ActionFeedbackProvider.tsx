import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

export type ActionFeedbackKind = "error" | "success";

export type ActionFeedbackPayload = {
  kind: ActionFeedbackKind;
  message: string;
  titleKey?: string;
  autoCloseMs?: number | null;
};

type ActionFeedbackContextValue = {
  feedback: ActionFeedbackPayload | null;
  showActionFeedback: (payload: ActionFeedbackPayload) => void;
  showErrorFeedback: (
    errorOrMessage: unknown,
    fallbackMessage?: string,
    options?: Omit<ActionFeedbackPayload, "kind" | "message">,
  ) => void;
  showSuccessFeedback: (
    message: string,
    options?: Omit<ActionFeedbackPayload, "kind" | "message">,
  ) => void;
  dismissActionFeedback: () => void;
};

const ActionFeedbackContext = createContext<ActionFeedbackContextValue | null>(null);
const DEFAULT_SUCCESS_AUTO_CLOSE_MS = 3200;

type ActionFeedbackProviderProps = {
  children: ReactNode;
};

function resolveActionFeedbackMessage(errorOrMessage: unknown, fallbackMessage: string): string {
  if (typeof errorOrMessage === "string" && errorOrMessage.trim()) {
    return errorOrMessage.trim();
  }
  if (
    errorOrMessage
    && typeof errorOrMessage === "object"
    && "message" in errorOrMessage
    && typeof errorOrMessage.message === "string"
    && errorOrMessage.message.trim()
  ) {
    return errorOrMessage.message.trim();
  }
  return fallbackMessage;
}

function ActionFeedbackModal({
  feedback,
  onClose,
}: {
  feedback: ActionFeedbackPayload;
  onClose: () => void;
}): JSX.Element {
  const { t } = useTranslation("common");
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const titleId = useId();
  const messageId = useId();
  const title = feedback.titleKey
    ? t(feedback.titleKey)
    : feedback.kind === "error"
      ? t("actionFeedback.dialog.errorTitle")
      : t("actionFeedback.dialog.successTitle");

  useEffect(() => {
    closeButtonRef.current?.focus();
  }, [feedback]);

  useEffect(() => {
    const handleEscapePress = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscapePress);
    return () => {
      document.removeEventListener("keydown", handleEscapePress);
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className="modal-card panel action-feedback-modal"
        data-kind={feedback.kind}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
      >
        <p className="eyebrow">
          {feedback.kind === "error"
            ? t("actionFeedback.dialog.errorEyebrow")
            : t("actionFeedback.dialog.successEyebrow")}
        </p>
        <h2 id={titleId} className="section-title modal-title">
          {title}
        </h2>
        <p id={messageId} className="modal-message">
          {feedback.message}
        </p>
        <div className="modal-actions">
          <button
            ref={closeButtonRef}
            type="button"
            className={feedback.kind === "error" ? "primary-button" : "secondary-button"}
            onClick={onClose}
          >
            {t("actionFeedback.dialog.close")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ActionFeedbackProvider({ children }: ActionFeedbackProviderProps): JSX.Element {
  const [feedback, setFeedback] = useState<ActionFeedbackPayload | null>(null);

  const dismissActionFeedback = useCallback((): void => {
    setFeedback(null);
  }, []);

  const showActionFeedback = useCallback((payload: ActionFeedbackPayload): void => {
    setFeedback({
      ...payload,
      autoCloseMs: payload.kind === "success"
        ? payload.autoCloseMs ?? DEFAULT_SUCCESS_AUTO_CLOSE_MS
        : null,
    });
  }, []);

  const showErrorFeedback = useCallback<ActionFeedbackContextValue["showErrorFeedback"]>((errorOrMessage, fallbackMessage = "", options) => {
    showActionFeedback({
      kind: "error",
      message: resolveActionFeedbackMessage(errorOrMessage, fallbackMessage),
      titleKey: options?.titleKey,
      autoCloseMs: null,
    });
  }, [showActionFeedback]);

  const showSuccessFeedback = useCallback<ActionFeedbackContextValue["showSuccessFeedback"]>((message, options) => {
    showActionFeedback({
      kind: "success",
      message,
      titleKey: options?.titleKey,
      autoCloseMs: options?.autoCloseMs,
    });
  }, [showActionFeedback]);

  useEffect(() => {
    if (!feedback || feedback.kind !== "success" || feedback.autoCloseMs == null || feedback.autoCloseMs <= 0) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setFeedback((current) => (current === feedback ? null : current));
    }, feedback.autoCloseMs);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [feedback]);

  const value = useMemo<ActionFeedbackContextValue>(() => ({
    feedback,
    showActionFeedback,
    showErrorFeedback,
    showSuccessFeedback,
    dismissActionFeedback,
  }), [dismissActionFeedback, feedback, showActionFeedback, showErrorFeedback, showSuccessFeedback]);

  return (
    <ActionFeedbackContext.Provider value={value}>
      {children}
      {feedback ? <ActionFeedbackModal feedback={feedback} onClose={dismissActionFeedback} /> : null}
    </ActionFeedbackContext.Provider>
  );
}

export function useActionFeedback(): ActionFeedbackContextValue {
  const context = useContext(ActionFeedbackContext);
  if (!context) {
    throw new Error("useActionFeedback must be used within ActionFeedbackProvider");
  }
  return context;
}

export function withActionFeedbackState(
  payload: ActionFeedbackPayload,
  currentState?: unknown,
): Record<string, unknown> {
  const baseState = currentState && typeof currentState === "object" && !Array.isArray(currentState)
    ? { ...(currentState as Record<string, unknown>) }
    : {};
  return {
    ...baseState,
    actionFeedback: payload,
  };
}

function readActionFeedbackFromState(state: unknown): ActionFeedbackPayload | null {
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    return null;
  }
  const rawFeedback = (state as Record<string, unknown>).actionFeedback;
  if (!rawFeedback || typeof rawFeedback !== "object" || Array.isArray(rawFeedback)) {
    return null;
  }
  const feedbackRecord = rawFeedback as Record<string, unknown>;
  const kind = feedbackRecord.kind === "error" ? "error" : feedbackRecord.kind === "success" ? "success" : null;
  const message = typeof feedbackRecord.message === "string" ? feedbackRecord.message.trim() : "";
  if (!kind || !message) {
    return null;
  }
  return {
    kind,
    message,
    titleKey: typeof feedbackRecord.titleKey === "string" && feedbackRecord.titleKey.trim() ? feedbackRecord.titleKey.trim() : undefined,
    autoCloseMs: typeof feedbackRecord.autoCloseMs === "number" ? feedbackRecord.autoCloseMs : undefined,
  };
}

function stripActionFeedbackFromState(state: unknown): Record<string, unknown> | null {
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    return null;
  }
  const nextState = { ...(state as Record<string, unknown>) };
  delete nextState.actionFeedback;
  return Object.keys(nextState).length > 0 ? nextState : null;
}

export function useRouteActionFeedback(state: unknown): void {
  const { showActionFeedback } = useActionFeedback();
  const consumedStateRef = useRef<unknown>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const feedback = readActionFeedbackFromState(state);
    if (!feedback) {
      if (consumedStateRef.current === state) {
        consumedStateRef.current = null;
      }
      return;
    }
    if (consumedStateRef.current === state) {
      return;
    }

    consumedStateRef.current = state;
    showActionFeedback(feedback);
    navigate(
      {
        pathname: location.pathname,
        search: location.search,
        hash: location.hash,
      },
      {
        replace: true,
        state: stripActionFeedbackFromState(state),
      },
    );
  }, [location.hash, location.pathname, location.search, navigate, showActionFeedback, state]);
}
