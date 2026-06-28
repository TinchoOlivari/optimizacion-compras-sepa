import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuthStore } from "@/store/authStore";

import { handleCarritoDomainEvent } from "../lib/cachePolicy";

export function CarritoCacheSync() {
  const queryClient = useQueryClient();
  const usuarioId = useAuthStore((state) => state.usuario?.id ?? null);
  const prevUsuarioId = useRef<number | null | undefined>(undefined);

  useEffect(() => {
    if (prevUsuarioId.current === undefined) {
      prevUsuarioId.current = usuarioId;
      return;
    }

    if (prevUsuarioId.current === usuarioId) {
      return;
    }

    void handleCarritoDomainEvent(queryClient, "session_changed");
    prevUsuarioId.current = usuarioId;
  }, [queryClient, usuarioId]);

  return null;
}
