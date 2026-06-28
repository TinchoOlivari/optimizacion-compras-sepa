import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { ProductoResumen } from "@tfg/shared";

import { buscarProductos } from "@/lib/api";

import { busquedaHabilitada } from "../lib/busqueda";
import { catalogoQueryKeys } from "../lib/queryKeys";

const BUSQUEDA_LIMIT = 5;

interface BuscarProductosResult {
  items: ProductoResumen[];
  total: number;
}

export function useBuscarProductos(query: string) {
  const q = query.trim();

  return useQuery<BuscarProductosResult>({
    queryKey: catalogoQueryKeys.busqueda(q, BUSQUEDA_LIMIT),
    queryFn: () => buscarProductos(q, BUSQUEDA_LIMIT),
    enabled: busquedaHabilitada(q),
    placeholderData: keepPreviousData,
    retry: 1,
  });
}
