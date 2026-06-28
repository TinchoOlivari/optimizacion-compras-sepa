import type { FiltrosGeo } from "@/features/preferencias/lib/filtrosGeo";

export const catalogoQueryKeys = {
  all: ["catalogo"] as const,
  busqueda: (query: string, limit: number) =>
    ["catalogo", "busqueda", query, limit] as const,
  detalleAll: () => ["catalogo", "detalle"] as const,
  detalle: (productoId: number, filtrosGeo: FiltrosGeo | undefined) =>
    ["catalogo", "detalle", productoId, filtrosGeo] as const,
};
