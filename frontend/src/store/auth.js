import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { ROLE } from "../constants/domain";

export const useAuthStore = create(
  persist(
    (set) => ({
      access: null,
      refresh: null,
      user: null,
      setSession: ({ access, refresh, user }) => set({ access, refresh, user }),
      setTokens: ({ access, refresh }) =>
        set((state) => ({ access, refresh: refresh ?? state.refresh })),
      setUser: (user) => set({ user }),
      clear: () => set({ access: null, refresh: null, user: null }),
    }),
    {
      name: "shebalocal-session",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ refresh: state.refresh, user: state.user }),
    },
  ),
);

export function selectIsAuthenticated(state) {
  return Boolean(state.refresh && state.user);
}

export function selectActiveRole(state) {
  return state.user?.activeRole ?? null;
}

export function selectIsProvider(state) {
  return state.user?.activeRole === ROLE.PROVIDER;
}
