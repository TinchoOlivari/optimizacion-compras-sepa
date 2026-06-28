import { useQuery } from "@tanstack/react-query";

import type { ProductoDetalleResponse } from "@/lib/api";
import { getProductoDetalle } from "@/lib/api";
import type { FiltrosGeo } from "@/features/preferencias/lib/filtrosGeo";

import { catalogoQueryKeys } from "../lib/queryKeys";

export function useProductoDetalle(productoId: number, filtrosGeo?: FiltrosGeo) {
  const idValido = Number.isFinite(productoId) && productoId > 0;
  const geoDisponible = filtrosGeo != null;

  return useQuery<ProductoDetalleResponse>({
    queryKey: catalogoQueryKeys.detalle(productoId, filtrosGeo),
    queryFn: async () => {
      if (!idValido) {
        throw new Error("Producto inválido.");
      }
      if (!filtrosGeo) {
        throw new Error("Ubicación requerida para cargar precios.");
      }
      return getProductoDetalle(productoId, filtrosGeo);
    },
    enabled: idValido && geoDisponible,
    retry: 1,
  });
}
