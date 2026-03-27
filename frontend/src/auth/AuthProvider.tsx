import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  fetchMe,
  loginUser,
  logoutUser,
  registerUser,
} from "./authApi";
import { clearAuthStorage, persistAuth, readStoredToken, readStoredUser } from "./storage";
import type { AuthUser, RegisterPayload } from "./types";

type AuthContextValue = {
  user: AuthUser | null;
  token: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (identifier: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<AuthUser | null>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps): JSX.Element {
  const [token, setToken] = useState<string>(() => readStoredToken());
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const clearAuth = useCallback(() => {
    clearAuthStorage();
    setToken("");
    setUser(null);
  }, []);

  const refreshMe = useCallback(async (): Promise<AuthUser | null> => {
    const activeToken = readStoredToken();
    if (!activeToken) {
      clearAuth();
      return null;
    }

    try {
      const result = await fetchMe(activeToken);
      setToken(activeToken);
      setUser(result.user);
      persistAuth(activeToken, result.user);
      return result.user;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearAuth();
        return null;
      }
      throw error;
    }
  }, [clearAuth]);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async (): Promise<void> => {
      try {
        if (token) {
          await refreshMe();
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [refreshMe, token]);

  const login = useCallback(async (identifier: string, password: string): Promise<AuthUser> => {
    const result = await loginUser(identifier, password);
    setToken(result.access_token);
    setUser(result.user);
    persistAuth(result.access_token, result.user);
    return result.user;
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    const activeToken = token || readStoredToken();
    try {
      if (activeToken) {
        await logoutUser(activeToken);
      }
    } catch {
      // stateless JWT logout: clear local auth even if endpoint is unavailable
    }
    clearAuth();
  }, [clearAuth, token]);

  const register = useCallback(async (payload: RegisterPayload): Promise<AuthUser> => {
    const activeToken = token || undefined;
    const result = await registerUser(payload, activeToken);
    return result.user;
  }, [token]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    isAuthenticated: Boolean(token && user),
    isLoading,
    login,
    logout,
    refreshMe,
    register,
  }), [isLoading, login, logout, refreshMe, register, token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
