import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { Providers } from "@/components/Providers";
import { routes } from "@/router";
import { useAuthStore } from "@/store/authStore";

function createCarritoActivoResponse(cantidadItems: number) {
  const items = Array.from({ length: cantidadItems }, (_, index) => ({
    id: index + 1,
    producto_id: 100 + index,
    cantidad: 1,
    producto: {
      id: 100 + index,
      codigo_ean: `779074230010${index}`,
      nombre: `Producto ${index + 1}`,
      marca: "Marca",
      presentacion: "1 unidad",
      url_imagen: null,
    },
  }));

  return {
    id: 1,
    titulo: "Mi carrito",
    activo: true,
    items,
  };
}

function createCarritosListaResponse(cantidadItems: number) {
  return {
    items: [
      {
        id: 1,
        titulo: "Mi carrito",
        activo: true,
        cantidad_items: cantidadItems,
        fecha_ultima_edicion: "2026-06-15T10:30:00",
      },
    ],
    total: 1,
  };
}

function mockCarritoCacheFlow(): void {
  let cantidadItems = 3;

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";

      if (url.includes("/api/v1/carritos/activo") && method === "GET") {
        return new Response(JSON.stringify(createCarritoActivoResponse(cantidadItems)), {
          status: 200,
        });
      }

      if (url.includes("/api/v1/carritos/1/items/1") && method === "DELETE") {
        cantidadItems = 2;
        return new Response(null, { status: 204 });
      }

      if (
        url.includes("/api/v1/carritos") &&
        !url.includes("/activo") &&
        !url.includes("/items") &&
        method === "GET"
      ) {
        return new Response(JSON.stringify(createCarritosListaResponse(cantidadItems)), {
          status: 200,
        });
      }

      return new Response(JSON.stringify({}), { status: 200 });
    }),
  );
}

function renderAuthenticatedRoute(initialEntry: string) {
  useAuthStore.setState({
    token: "valid-token",
    usuario: { id: 1, nombre: "Ana", correo: "ana@test.com" },
  });

  const router = createMemoryRouter(routes, { initialEntries: [initialEntry] });

  render(
    <Providers>
      <RouterProvider router={router} />
    </Providers>,
  );

  return router;
}

describe("carrito cache cross-page", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("actualiza cantidad_items en /carritos tras eliminar item en home", async () => {
    mockCarritoCacheFlow();

    const router = renderAuthenticatedRoute("/");

    await waitFor(() => {
      expect(screen.getByText("Producto 3")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /eliminar producto 1 del carrito/i }));

    await waitFor(() => {
      expect(screen.queryByText("Producto 3")).not.toBeInTheDocument();
      expect(screen.getByText(/2 productos/i)).toBeInTheDocument();
    });

    await router.navigate("/carritos");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /mis carritos/i })).toBeInTheDocument();
      expect(screen.getByText(/2 productos/i)).toBeInTheDocument();
    });
  });
});
