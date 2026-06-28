import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { usePreferencias } from "../hooks/usePreferencias";
import { filtrosGeoDesdePreferencias } from "../lib/filtrosGeo";
import { preferenciasQueryKeys } from "../lib/queryKeys";

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("usePreferencias", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            radio_km: 5,
            max_paradas: 3,
            preferencia: "MENOR_PRECIO",
            origen: { latitud: -31.4175, longitud: -64.1833 },
            por_defecto_aplicado: [],
          }),
          { status: 200 },
        ),
      ),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("carga preferencias con query key de dominio", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(() => usePreferencias(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(queryClient.getQueryState(preferenciasQueryKeys.actuales())?.data).toEqual({
      radio_km: 5,
      max_paradas: 3,
      preferencia: "MENOR_PRECIO",
      origen: { latitud: -31.4175, longitud: -64.1833 },
      por_defecto_aplicado: [],
    });

    expect(filtrosGeoDesdePreferencias(result.current.data)).toEqual({
      lat: -31.4175,
      lon: -64.1833,
      radio_km: 5,
    });
  });
});
