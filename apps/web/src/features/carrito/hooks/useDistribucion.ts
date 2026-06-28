import { useQuery } from "@tanstack/react-query";

import { getCarritoDetalle, getDistribucionVigente } from "@/lib/api";

import { carritoQueryKeys } from "../lib/queryKeys";

export function useDistribucion() {
  return useQuery({
    queryKey: carritoQueryKeys.distribucion(),
    queryFn: async () => {
      const carrito = await getCarritoDetalle();
      if (!carrito) {
        throw new Error("No tenés un carrito activo.");
      }
      const resultado = await getDistribucionVigente(carrito.id);
      return { carritoId: carrito.id, resultado };
    },
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: "always",
    retry: 1,
  });
}
