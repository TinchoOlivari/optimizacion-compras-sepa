import { useCallback, useEffect, useMemo, useState } from "react";

import {
  CARRITO_ANONIMO_STORAGE_KEY,
  EVENTO_CARRITO_ANONIMO_ACTUALIZADO,
  getCantidadTotalItems,
  getCarritoAnonimo,
  type CarritoAnonimoItem,
} from "@/lib/carrito-anonimo";

export function useCarritoAnonimo() {
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => {
    setTick((actual) => actual + 1);
  }, []);

  useEffect(() => {
    const onUpdate = () => refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === CARRITO_ANONIMO_STORAGE_KEY) {
        refresh();
      }
    };

    window.addEventListener(EVENTO_CARRITO_ANONIMO_ACTUALIZADO, onUpdate);
    window.addEventListener("storage", onStorage);

    return () => {
      window.removeEventListener(EVENTO_CARRITO_ANONIMO_ACTUALIZADO, onUpdate);
      window.removeEventListener("storage", onStorage);
    };
  }, [refresh]);

  const items = useMemo<CarritoAnonimoItem[]>(() => {
    void tick;
    return getCarritoAnonimo().items;
  }, [tick]);

  const totalItems = useMemo<number>(() => {
    void tick;
    return getCantidadTotalItems();
  }, [tick]);

  return { items, totalItems, refresh };
}
