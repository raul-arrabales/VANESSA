import { useEffect, useRef, useState } from "react";
import { streamCloudTrafficEvents, type CloudTrafficDirection } from "../../api/cloudTraffic";

const PULSE_DURATION_MS = 900;
const RECONNECT_DELAY_MS = 1500;

type CloudTrafficIndicatorState = {
  uploadActive: boolean;
  downloadActive: boolean;
};

export function useCloudTrafficIndicators({
  isAuthenticated,
  mode,
  token,
}: {
  isAuthenticated: boolean;
  mode: "offline" | "online" | null;
  token: string;
}): CloudTrafficIndicatorState {
  const [uploadActive, setUploadActive] = useState(false);
  const [downloadActive, setDownloadActive] = useState(false);
  const pulseTimersRef = useRef<Record<CloudTrafficDirection, number | null>>({
    egress: null,
    ingress: null,
  });

  useEffect(() => {
    if (!isAuthenticated || mode !== "online" || !token) {
      setUploadActive(false);
      setDownloadActive(false);
      return;
    }

    const abortController = new AbortController();
    let stopped = false;
    let reconnectTimer: number | null = null;

    const pulse = (direction: CloudTrafficDirection): void => {
      const setActive = direction === "egress" ? setUploadActive : setDownloadActive;
      setActive(true);
      const existingTimer = pulseTimersRef.current[direction];
      if (existingTimer !== null) {
        window.clearTimeout(existingTimer);
      }
      pulseTimersRef.current[direction] = window.setTimeout(() => {
        setActive(false);
        pulseTimersRef.current[direction] = null;
      }, PULSE_DURATION_MS);
    };

    const connect = async (): Promise<void> => {
      while (!stopped) {
        try {
          await streamCloudTrafficEvents(token, {
            signal: abortController.signal,
            onEvent: (event) => {
              if (event.direction === "egress" || event.direction === "ingress") {
                pulse(event.direction);
              }
            },
          });
        } catch (error) {
          if (abortController.signal.aborted) {
            return;
          }
        }
        await new Promise<void>((resolve) => {
          reconnectTimer = window.setTimeout(resolve, RECONNECT_DELAY_MS);
        });
      }
    };

    void connect();

    return () => {
      stopped = true;
      abortController.abort();
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
    };
  }, [isAuthenticated, mode, token]);

  useEffect(() => () => {
    for (const timer of Object.values(pulseTimersRef.current)) {
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    }
  }, []);

  return { uploadActive, downloadActive };
}
