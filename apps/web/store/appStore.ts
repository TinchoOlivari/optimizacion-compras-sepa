"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import { clearCarritoAnonimo } from "@/lib/carrito-anonimo";

interface AppState {
  compraGuiadaActivaId: number | null;
  carritoAnonimoId: number | null;

  setCompraGuiadaActiva: (id: number | null) => void;
  sincronizarCarritoLogout: () => void;
  reset: () => void;
}

const INITIAL_STATE = {
  compraGuiadaActivaId: null,
  carritoAnonimoId: null,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      ...INITIAL_STATE,

      setCompraGuiadaActiva: (id) => set({ compraGuiadaActivaId: id }),

      sincronizarCarritoLogout: () => {
        clearCarritoAnonimo();
        set({ ...INITIAL_STATE });
      },

      reset: () => set({ ...INITIAL_STATE }),
    }),
    {
      name: "tfg-app-state",
      partialize: (state) => ({
        compraGuiadaActivaId: state.compraGuiadaActivaId,
        carritoAnonimoId: state.carritoAnonimoId,
      }),
    },
  ),
);
