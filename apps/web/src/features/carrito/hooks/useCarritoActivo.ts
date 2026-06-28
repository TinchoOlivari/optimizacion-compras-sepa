import { useQuery } from "@tanstack/react-query";

import type { CarritoDetalle } from "@tfg/shared";

import { getCarritoDetalle } from "@/lib/api";

import { carritoQueryKeys } from "../lib/queryKeys";

export function useCarritoActivo(autenticado: boolean) {
  return useQuery<CarritoDetalle | null>({
    queryKey: carritoQueryKeys.activo(),
    queryFn: getCarritoDetalle,
    enabled: autenticado,
  });
}
