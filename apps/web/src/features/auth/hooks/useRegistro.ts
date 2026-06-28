import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { registrarUsuario } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

import { esErrorCorreoDuplicado, mensajeDesdeError } from "../lib/errors";
import { useAuthAnonimoSnapshot } from "./useAuthAnonimoSnapshot";

const MENSAJE_FALLBACK = "No pudimos conectar con el servidor. Intentá de nuevo.";

interface RegistroInput {
  nombre: string;
  correo: string;
  password: string;
}

export function useRegistro() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const { obtenerParaAuth, limpiarSiTieneItems } = useAuthAnonimoSnapshot();

  const mutation = useMutation({
    mutationFn: async ({ nombre, correo, password }: RegistroInput) => {
      const carritoAnonimo = obtenerParaAuth();
      const resultado = await registrarUsuario({ nombre, correo, password, carritoAnonimo });
      return { ...resultado, carritoAnonimo };
    },
    onSuccess: ({ token, usuario, carritoAnonimo }) => {
      setAuth(token, usuario);
      limpiarSiTieneItems(carritoAnonimo);
      navigate("/");
    },
  });

  const mensajeError = mutation.error
    ? mensajeDesdeError(mutation.error, MENSAJE_FALLBACK)
    : undefined;

  return {
    registrar: mutation.mutateAsync,
    cargando: mutation.isPending,
    errorGeneral: mensajeError && !esErrorCorreoDuplicado(mutation.error) ? mensajeError : undefined,
    errorCorreo: mensajeError && esErrorCorreoDuplicado(mutation.error) ? mensajeError : undefined,
    resetError: mutation.reset,
  };
}
