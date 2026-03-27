import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { AuthUser } from "../../../auth/types";
import { ApiError } from "../../../auth/authApi";
import { activatePendingUser, listPendingUsers, promotePendingUser } from "../api/adminApprovals";

type UseAdminApprovalsResult = {
  pendingUsers: AuthUser[];
  isLoading: boolean;
  actionUserId: number | null;
  error: string;
  refreshPendingUsers: () => Promise<void>;
  activateUser: (targetUser: AuthUser) => Promise<AuthUser>;
  promoteUserToAdmin: (targetUser: AuthUser) => Promise<AuthUser>;
};

export function useAdminApprovals(token: string): UseAdminApprovalsResult {
  const { t } = useTranslation("common");
  const [pendingUsers, setPendingUsers] = useState<AuthUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionUserId, setActionUserId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const handleError = useCallback((loadError: unknown): void => {
    if (loadError instanceof ApiError) {
      setError(loadError.message);
    } else {
      setError(t("auth.error.unknown"));
    }
  }, [t]);

  const refreshPendingUsers = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError("");
    try {
      const users = await listPendingUsers(token);
      setPendingUsers(users);
    } catch (loadError) {
      handleError(loadError);
    } finally {
      setIsLoading(false);
    }
  }, [handleError, token]);

  useEffect(() => {
    void refreshPendingUsers();
  }, [refreshPendingUsers]);

  const activateUser = useCallback(async (targetUser: AuthUser): Promise<AuthUser> => {
    setActionUserId(targetUser.id);
    setError("");
    try {
      return await activatePendingUser(targetUser.id, token);
    } finally {
      setActionUserId(null);
    }
  }, [token]);

  const promoteUserToAdmin = useCallback(async (targetUser: AuthUser): Promise<AuthUser> => {
    setActionUserId(targetUser.id);
    setError("");
    try {
      return await promotePendingUser(targetUser.id, "admin", token);
    } finally {
      setActionUserId(null);
    }
  }, [token]);

  return {
    pendingUsers,
    isLoading,
    actionUserId,
    error,
    refreshPendingUsers,
    activateUser,
    promoteUserToAdmin,
  };
}
