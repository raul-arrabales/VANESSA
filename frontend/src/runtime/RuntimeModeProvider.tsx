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
import {
  getRuntimeProfile,
  setRuntimeProfile,
  type RuntimeProfile,
  type RuntimeProfileResult,
  type RuntimeProfileSource,
} from "../api/runtime";

type RuntimeModeContextValue = {
  mode: RuntimeProfile | null;
  isLocked: boolean;
  source: RuntimeProfileSource | null;
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
  const [isLocked, setIsLocked] = useState<boolean>(false);
  const [source, setSource] = useState<RuntimeProfileSource | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const loadedTokenRef = useRef<string>("");

  const applyRuntimeProfileState = useCallback((result: RuntimeProfileResult): void => {
    setModeState(result.profile);
    setIsLocked(result.locked);
    setSource(result.source);
  }, []);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      loadedTokenRef.current = "";
      setModeState(null);
      setIsLocked(false);
      setSource(null);
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
        applyRuntimeProfileState(result);
      })
      .catch((loadError: unknown) => {
        if (loadError instanceof ApiError) {
          setError(loadError.message);
          return;
        }
        setError("settings.runtime.error.load");
      })
      .finally(() => setIsLoading(false));
  }, [applyRuntimeProfileState, isAuthenticated, token]);

  const setMode = useCallback(async (nextMode: RuntimeProfile): Promise<RuntimeProfile> => {
    if (!token) {
      throw new ApiError("Authentication required", 401, "missing_auth");
    }

    const previousMode = mode;
    const previousIsLocked = isLocked;
    const previousSource = source;
    setModeState(nextMode);
    setError("");
    setIsSaving(true);

    try {
      const result = await setRuntimeProfile(token, nextMode);
      applyRuntimeProfileState(result);
      return result.profile;
    } catch (saveError) {
      setModeState(previousMode);
      setIsLocked(previousIsLocked);
      setSource(previousSource);
      throw saveError;
    } finally {
      setIsSaving(false);
    }
  }, [applyRuntimeProfileState, isLocked, mode, source, token]);

  const value = useMemo<RuntimeModeContextValue>(() => ({
    mode,
    isLocked,
    source,
    isLoading,
    isSaving,
    error,
    setMode,
  }), [error, isLoading, isLocked, isSaving, mode, setMode, source]);

  return <RuntimeModeContext.Provider value={value}>{children}</RuntimeModeContext.Provider>;
}

export function useRuntimeMode(): RuntimeModeContextValue {
  const context = useContext(RuntimeModeContext);
  if (!context) {
    throw new Error("useRuntimeMode must be used within RuntimeModeProvider");
  }
  return context;
}
