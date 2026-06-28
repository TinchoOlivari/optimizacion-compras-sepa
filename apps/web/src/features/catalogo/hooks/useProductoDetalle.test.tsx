import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { useProductoDetalle } from "./useProductoDetalle";

vi.mock("@/lib/api", () => ({
  getProductoDetalle: vi.fn(),
}));

import { getProductoDetalle } from "@/lib/api";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useProductoDetalle", () => {
  it("no consulta la API sin filtros geo", () => {
    renderHook(() => useProductoDetalle(42, undefined), { wrapper: createWrapper() });

    expect(getProductoDetalle).not.toHaveBeenCalled();
  });

  it("consulta la API con filtros geo", async () => {
    vi.mocked(getProductoDetalle).mockResolvedValue({
      producto: {
        id: 42,
        codigo_ean: "7790580492432",
        nombre: "Leche Entera",
        marca: null,
        presentacion: null,
        url_imagen: null,
      },
      precios: [],
      filtro_radio_activo: true,
      mensaje: null,
    });

    const filtrosGeo = { lat: -31.4, lon: -64.2, radio_km: 5 };

    renderHook(() => useProductoDetalle(42, filtrosGeo), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(getProductoDetalle).toHaveBeenCalledWith(42, filtrosGeo);
    });
  });
});
