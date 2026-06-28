import { useMutation, useQueryClient } from "@tanstack/react-query";

import { actualizarNombre } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useToastStore } from "@/store/toastStore";

export function useActualizarNombre() {
  const queryClient = useQueryClient();
  const updateNombre = useAuthStore((state) => state.updateNombre);
  const addToast = useToastStore((state) => state.addToast);

  const actualizarMutation = useMutation({
    mutationFn: actualizarNombre,
    onSuccess: (data) => {
      updateNombre(data.nombre);
      queryClient.invalidateQueries({ queryKey: ["preferencias"] });
      addToast({ message: "Nombre actualizado.", variant: "success" });
    },
    onError: (error: Error) => {
      addToast({
        message: error.message || "No pudimos actualizar el nombre.",
        variant: "error",
      });
    },
  });

  return { actualizarMutation };
}
