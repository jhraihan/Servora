import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { COMPARE_LIMIT } from "../constants/domain";

export const useCompareStore = create(
  persist(
    (set, get) => ({
      ids: [],
      toggle: (id) =>
        set((state) => {
          if (state.ids.includes(id)) {
            return { ids: state.ids.filter((x) => x !== id) };
          }
          if (state.ids.length >= COMPARE_LIMIT) return state;
          return { ids: [...state.ids, id] };
        }),
      has: (id) => get().ids.includes(id),
      clear: () => set({ ids: [] }),
    }),
    {
      name: "shebalocal-compare",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
