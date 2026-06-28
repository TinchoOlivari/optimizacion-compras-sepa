import { useCallback } from "react";

import { useCarritoAnonimo } from "@/features/carrito/hooks/useCarritoAnonimo";
import {
  clearCarritoAnonimo,
  serializeForAuth,
  type CarritoAnonimoItem,
} from "@/lib/carrito-anonimo";

export function useAuthAnonimoSnapshot() {
  const { totalItems } = useCarritoAnonimo();

  const obtenerParaAuth = useCallback((): CarritoAnonimoItem[] => serializeForAuth(), []);

  const limpiarSiTieneItems = useCallback((items: CarritoAnonimoItem[]) => {
    if (items.length > 0) {
      clearCarritoAnonimo();
    }
  }, []);

  return {
    cantidadItems: totalItems,
    obtenerParaAuth,
    limpiarSiTieneItems,
  };
}
