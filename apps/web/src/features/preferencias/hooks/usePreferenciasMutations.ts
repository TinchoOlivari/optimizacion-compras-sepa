import { useMutation, useQueryClient } from "@tanstack/react-query";

import { updatePreferencias } from "@/lib/api";
import { useToastStore } from "@/store/toastStore";

import { invalidatePreferenciasYDependientes } from "../lib/cachePolicy";

export function usePreferenciasMutations() {
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);

  const guardarMutation = useMutation({
    mutationFn: updatePreferencias,
    onSuccess: async () => {
      await invalidatePreferenciasYDependientes(queryClient);
      addToast({ message: "Preferencias guardadas.", variant: "success" });
    },
    onError: (error: Error) => {
      addToast({
        message: error.message || "No pudimos guardar las preferencias.",
        variant: "error",
      });
    },
  });

  return { guardarMutation };
}
