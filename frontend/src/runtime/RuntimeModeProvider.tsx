import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError } from "../auth/authApi";
import { useAuth } from "../auth/AuthProvider";
import { getRuntimeProfile, setRuntimeProfile, type RuntimeProfile } from "../api/runtime";

type RuntimeModeContextValue = {
  mode: RuntimeProfile | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string;
  setMode: (profile: RuntimeProfile) => Promise<RuntimeProfile>;
};

const RuntimeModeContext = createContext<RuntimeModeContextValue | null>(null);

type RuntimeModeProviderProps = {
  children: ReactNode;
};

export function RuntimeModeProvider({ children }: RuntimeModeProviderProps): JSX.Element {
  const { token, isAuthenticated } = useAuth();
  const [mode, setModeState] = useState<RuntimeProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const loadedTokenRef = useRef<string>("");

  useEffect(() => {
    if (!isAuthenticated || !token) {
      loadedTokenRef.current = "";
      setModeState(null);
      setError("");
      setIsLoading(false);
      return;
    }

    if (loadedTokenRef.current === token) {
      return;
    }

    loadedTokenRef.current = token;
    setIsLoading(true);
    setError("");

    getRuntimeProfile(token)
      .then((result) => {
        setModeState(result.profile);
      })
      .catch((loadError: unknown) => {
        if (loadError instanceof ApiError) {
          setError(loadError.message);
          return;
        }
        setError("settings.runtime.error.load");
      })
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, token]);

  const setMode = useCallback(async (nextMode: RuntimeProfile): Promise<RuntimeProfile> => {
    if (!token) {
      throw new ApiError("Authentication required", 401, "missing_auth");
    }

    const previousMode = mode;
    setModeState(nextMode);
    setError("");
    setIsSaving(true);

    try {
      const result = await setRuntimeProfile(token, nextMode);
      setModeState(result.profile);
      return result.profile;
    } catch (saveError) {
      setModeState(previousMode);
      if (saveError instanceof ApiError) {
        setError(saveError.message);
      } else {
        setError("runtimeMode.updateFailed");
      }
      throw saveError;
    } finally {
      setIsSaving(false);
    }
  }, [mode, token]);

  const value = useMemo<RuntimeModeContextValue>(() => ({
    mode,
    isLoading,
    isSaving,
    error,
    setMode,
  }), [error, isLoading, isSaving, mode, setMode]);

  return <RuntimeModeContext.Provider value={value}>{children}</RuntimeModeContext.Provider>;
}

export function useRuntimeMode(): RuntimeModeContextValue {
  const context = useContext(RuntimeModeContext);
  if (!context) {
    throw new Error("useRuntimeMode must be used within RuntimeModeProvider");
  }
  return context;
}
