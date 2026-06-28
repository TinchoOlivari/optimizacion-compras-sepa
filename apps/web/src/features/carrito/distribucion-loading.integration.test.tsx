import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { Providers } from "@/components/Providers";
import { routes } from "@/router";
import { useAuthStore } from "@/store/authStore";

const PRODUCTO_LECHE = {
  id: 1,
  codigo_ean: "7790742300101",
  nombre: "Leche Entera Larga Vida",
  marca: "La Serenísima",
  presentacion: "1 Litro",
  url_imagen: null,
};

const PRODUCTO_YOGUR = {
  id: 2,
  codigo_ean: "7790742300202",
  nombre: "Yogur Natural",
  marca: "La Serenísima",
  presentacion: "190 g",
  url_imagen: null,
};

function createDistribucionResponse(
  productos: Array<{ item_carrito_id: number; nombre_producto: string }>,
) {
  return {
    fecha_calculo: "2026-06-15T12:00:00",
    costo_total_estimado: 14500,
    ahorro_estimado: 2300,
    configuracion: {
      radio_km: 5,
      max_paradas: 3,
      preferencia: "MENOR_PRECIO",
      por_defecto_aplicado: [],
    },
    asignaciones: [
      {
        sucursal_id: 101,
        sucursal: "Día Av. Rivadavia",
        comercio: "Supermercado Día",
        subtotal: 8500,
        items: productos.map((producto) => ({
          item_carrito_id: producto.item_carrito_id,
          producto_id: producto.item_carrito_id,
          nombre_producto: producto.nombre_producto,
          cantidad: 1,
          precio_unitario: 1250,
          subtotal: 1250,
        })),
      },
    ],
    items_no_asignados: [],
    ruteo: { distancia_total_km: 2.4, paradas: [] },
    mensaje: null,
  };
}

function mockRedistribucionFlow(): void {
  let nextItemId = 2;
  let carritoItems = [
    {
      id: 1,
      producto_id: 1,
      cantidad: 1,
      producto: PRODUCTO_LECHE,
    },
  ];
  let distribuirCalls = 0;

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";

      if (url.includes("/api/v1/preferencias")) {
        return new Response(
          JSON.stringify({
            radio_km: 5,
            max_paradas: 3,
            preferencia: "MENOR_PRECIO",
            origen: { latitud: -31.4175, longitud: -64.1833 },
            por_defecto_aplicado: [],
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/v1/carritos/activo") && method === "GET") {
        return new Response(
          JSON.stringify({
            id: 1,
            titulo: "Mi carrito",
            activo: true,
            items: carritoItems,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/v1/productos/buscar") && method === "GET") {
        return new Response(
          JSON.stringify({
            items: [PRODUCTO_YOGUR],
            total: 1,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/v1/carritos/1/items") && method === "POST") {
        carritoItems = [
          ...carritoItems,
          {
            id: nextItemId,
            producto_id: 2,
            cantidad: 1,
            producto: PRODUCTO_YOGUR,
          },
        ];
        nextItemId += 1;
        return new Response(
          JSON.stringify({
            id: 2,
            producto_id: 2,
            cantidad: 1,
            producto: PRODUCTO_YOGUR,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/distribuir") && method === "POST") {
        distribuirCalls += 1;
        const callNumber = distribuirCalls;

        if (callNumber === 1) {
          return new Response(
            JSON.stringify(
              createDistribucionResponse([
                { item_carrito_id: 1, nombre_producto: PRODUCTO_LECHE.nombre },
              ]),
            ),
            { status: 200 },
          );
        }

        return new Response(
          JSON.stringify(
            await new Promise((resolve) => {
              window.setTimeout(() => {
                resolve(
                  createDistribucionResponse([
                    { item_carrito_id: 1, nombre_producto: PRODUCTO_LECHE.nombre },
                    { item_carrito_id: 2, nombre_producto: PRODUCTO_YOGUR.nombre },
                  ]),
                );
              }, 100);
            }),
          ),
          { status: 200 },
        );
      }

      if (
        url.includes("/api/v1/carritos") &&
        !url.includes("/activo") &&
        !url.includes("/items") &&
        !url.includes("/distribuir") &&
        method === "GET"
      ) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 1,
                titulo: "Mi carrito",
                activo: true,
                cantidad_items: carritoItems.length,
                fecha_ultima_edicion: "2026-06-15T10:30:00",
              },
            ],
            total: 1,
          }),
          { status: 200 },
        );
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

describe("distribucion loading", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("muestra Cargando y no resultados viejos al redistribuir tras agregar items", async () => {
    mockRedistribucionFlow();

    renderAuthenticatedRoute("/");

    await waitFor(() => {
      expect(screen.getByText(/Leche Entera Larga Vida/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /distribuir carrito/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /distribuir compra/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /distribuir compra/i }));

    await waitFor(() => {
      expect(screen.getByText(/Leche Entera Larga Vida/)).toBeInTheDocument();
      expect(screen.queryByText(/cargando/i)).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /volver/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /distribuir compra/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /volver/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /distribuir carrito/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/buscar producto/i), {
      target: { value: "yogur" },
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /agregar yogur natural al carrito/i }),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /agregar yogur natural al carrito/i }));

    await waitFor(() => {
      expect(screen.getByText(/Yogur Natural/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /distribuir carrito/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /distribuir compra/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /distribuir compra/i }));

    await waitFor(() => {
      expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    });

    expect(screen.queryByText(/Leche Entera Larga Vida/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Yogur Natural/)).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Leche Entera Larga Vida/)).toBeInTheDocument();
      expect(screen.getByText(/Yogur Natural/)).toBeInTheDocument();
      expect(screen.queryByText(/cargando/i)).not.toBeInTheDocument();
    });
  });
});
