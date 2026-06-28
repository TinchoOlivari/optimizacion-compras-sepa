import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { iniciarSesion } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

import { mensajeDesdeError } from "../lib/errors";
import { useAuthAnonimoSnapshot } from "./useAuthAnonimoSnapshot";

const MENSAJE_FALLBACK = "No pudimos iniciar sesión. Verificá tus credenciales.";

interface LoginInput {
  correo: string;
  password: string;
}

export function useLogin() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const { obtenerParaAuth, limpiarSiTieneItems } = useAuthAnonimoSnapshot();

  const mutation = useMutation({
    mutationFn: async ({ correo, password }: LoginInput) => {
      const carritoAnonimo = obtenerParaAuth();
      const resultado = await iniciarSesion({ correo, password, carritoAnonimo });
      return { ...resultado, carritoAnonimo };
    },
    onSuccess: ({ token, usuario, carritoAnonimo }) => {
      setAuth(token, usuario);
      limpiarSiTieneItems(carritoAnonimo);
      navigate("/");
    },
  });

  return {
    login: mutation.mutateAsync,
    cargando: mutation.isPending,
    errorGeneral: mutation.error
      ? mensajeDesdeError(mutation.error, MENSAJE_FALLBACK)
      : undefined,
    resetError: mutation.reset,
  };
}
