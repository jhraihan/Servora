import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { auth } from "../api/endpoints";
import { ROLE } from "../constants/domain";
import { selectIsAuthenticated, useAuthStore } from "../store/auth";

export function useSession() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore(selectIsAuthenticated);
  const setSession = useAuthStore((s) => s.setSession);
  const setUser = useAuthStore((s) => s.setUser);
  const clear = useAuthStore((s) => s.clear);

  const login = useCallback(
    async (credentials) => {
      const session = await auth.login(credentials);
      setSession(session);
      queryClient.clear();
      return session.user;
    },
    [setSession, queryClient],
  );

  const logout = useCallback(async () => {
    const { refresh } = useAuthStore.getState();
    try {
      if (refresh) await auth.logout(refresh);
    } catch {
      return;
    } finally {
      clear();
      queryClient.clear();
    }
  }, [clear, queryClient]);

  const switchRole = useCallback(
    async (role) => {
      const next = await auth.switchRole(role);
      setUser(next);
      queryClient.clear();
      return next;
    },
    [setUser, queryClient],
  );

  return {
    user,
    isAuthenticated,
    isProvider: user?.activeRole === ROLE.PROVIDER,
    isCustomer: user?.activeRole === ROLE.CUSTOMER,
    login,
    logout,
    switchRole,
  };
}
