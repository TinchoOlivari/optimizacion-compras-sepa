import type { QueryClient } from "@tanstack/react-query";

import { catalogoQueryKeys } from "@/features/catalogo/lib/queryKeys";

import { preferenciasQueryKeys } from "./queryKeys";

export async function invalidatePreferenciasYDependientes(
  queryClient: QueryClient,
): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: preferenciasQueryKeys.all }),
    queryClient.invalidateQueries({ queryKey: catalogoQueryKeys.detalleAll() }),
  ]);
}
