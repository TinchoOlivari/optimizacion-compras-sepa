import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";

import { getCarritoAnonimo, loadSnapshot } from "@/lib/carrito-anonimo";
import { useAuthStore } from "@/store/authStore";

import { useAuthAnonimoSnapshot } from "./hooks/useAuthAnonimoSnapshot";
import { useLogin } from "./hooks/useLogin";
import { useRegistro } from "./hooks/useRegistro";

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe("useAuthAnonimoSnapshot", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    loadSnapshot([]);
  });

  afterEach(() => {
    cleanup();
    useAuthStore.getState().logout();
    loadSnapshot([]);
  });

  it("expone la cantidad de ítems del carrito anónimo", () => {
    loadSnapshot([
      { productoId: 1, cantidad: 2 },
      { productoId: 2, cantidad: 1 },
    ]);

    const { result } = renderHook(() => useAuthAnonimoSnapshot());

    expect(result.current.cantidadItems).toBe(3);
    expect(result.current.obtenerParaAuth()).toEqual([
      { productoId: 1, cantidad: 2 },
      { productoId: 2, cantidad: 1 },
    ]);
  });
});

describe("useLogin", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    loadSnapshot([{ productoId: 10, cantidad: 2 }]);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    useAuthStore.getState().logout();
    loadSnapshot([]);
  });

  it("envía el carrito anónimo, autentica y limpia el storage local", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const body = JSON.parse(String(init?.body ?? "{}")) as {
        correo: string;
        password: string;
        carritoAnonimo: { productoId: number; cantidad: number }[];
      };

      expect(url).toContain("/api/v1/auth/login");
      expect(body.carritoAnonimo).toEqual([{ productoId: 10, cantidad: 2 }]);

      return new Response(
        JSON.stringify({
          token: "token-test",
          usuario: { id: 1, nombre: "Ana", correo: "ana@test.com" },
        }),
        { status: 200 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    });

    const { result } = renderHook(() => useLogin(), {
      wrapper: createWrapper(queryClient),
    });

    await result.current.login({ correo: "ana@test.com", password: "password123" });

    await waitFor(() => {
      expect(useAuthStore.getState().token).toBe("token-test");
    });

    expect(useAuthStore.getState().usuario).toEqual({
      id: 1,
      nombre: "Ana",
      correo: "ana@test.com",
    });
    expect(getCarritoAnonimo().items).toEqual([]);
  });
});

describe("useRegistro", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    loadSnapshot([]);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    useAuthStore.getState().logout();
    loadSnapshot([]);
  });

  it("expone error de correo duplicado ante respuesta 409", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: { codigo: "CORREO_DUPLICADO", mensaje: "El correo ya está registrado." },
          }),
          { status: 409 },
        ),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    });

    const { result } = renderHook(() => useRegistro(), {
      wrapper: createWrapper(queryClient),
    });

    await expect(
      result.current.registrar({
        nombre: "Ana",
        correo: "ana@test.com",
        password: "password123",
      }),
    ).rejects.toThrow();

    await waitFor(() => {
      expect(result.current.errorCorreo).toBe("El correo ya está registrado.");
    });

    expect(result.current.errorGeneral).toBeUndefined();
    expect(useAuthStore.getState().token).toBeNull();
  });
});
