import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UsuarioAutenticado {
  id: number;
  nombre: string;
  correo: string;
}

interface AuthState {
  token: string | null;
  usuario: UsuarioAutenticado | null;
  setAuth: (token: string, usuario: UsuarioAutenticado) => void;
  updateNombre: (nombre: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      usuario: null,
      setAuth: (token, usuario) => set({ token, usuario }),
      updateNombre: (nombre) =>
        set((state) => ({
          usuario: state.usuario ? { ...state.usuario, nombre } : null,
        })),
      logout: () => set({ token: null, usuario: null }),
    }),
    {
      name: "tfg-auth",
      partialize: (state) => ({
        token: state.token,
        usuario: state.usuario,
      }),
    },
  ),
);
