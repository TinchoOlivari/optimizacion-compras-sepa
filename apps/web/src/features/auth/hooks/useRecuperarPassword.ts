import { useMutation } from "@tanstack/react-query";

import { solicitarRecuperacion } from "@/lib/api";

const MENSAJE_ERROR = "No pudimos enviar el enlace. Intentá nuevamente.";

export function useRecuperarPassword() {
  const mutation = useMutation({
    mutationFn: (correo: string) => solicitarRecuperacion(correo),
  });

  return {
    solicitar: mutation.mutateAsync,
    enviando: mutation.isPending,
    mensaje: mutation.isSuccess ? mutation.data.mensaje : undefined,
    error: mutation.isError ? MENSAJE_ERROR : undefined,
    reset: mutation.reset,
  };
}
