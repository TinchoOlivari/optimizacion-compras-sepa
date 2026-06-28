import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { catalogoQueryKeys } from "@/features/catalogo/lib/queryKeys";

import { invalidatePreferenciasYDependientes } from "./cachePolicy";
import { preferenciasQueryKeys } from "./queryKeys";

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe("cachePolicy preferencias", () => {
  it("invalida preferencias y queries geo-dependientes al guardar", async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await invalidatePreferenciasYDependientes(queryClient);

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: preferenciasQueryKeys.all,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: catalogoQueryKeys.detalleAll(),
    });
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
  });
});
