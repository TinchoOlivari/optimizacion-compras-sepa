import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { Providers } from "@/components/Providers";
import { routes } from "@/router";
import { useAuthStore } from "@/store/authStore";

function mockBackendResponses(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.includes("/api/v1/preferencias")) {
        return new Response(
          JSON.stringify({
            radio_km: 10,
            max_paradas: 3,
            preferencia: "MENOR_PRECIO",
            origen: { latitud: -31.4175, longitud: -64.1833 },
            por_defecto_aplicado: [],
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/v1/carritos/activo")) {
        return new Response(
          JSON.stringify({
            id: 1,
            titulo: null,
            activo: true,
            items: [],
          }),
          { status: 200 },
        );
      }

      if (url.includes("/distribuir") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            id: 20,
            fecha_calculo: "2026-06-15T12:00:00",
            costo_total_estimado: 14500,
            ahorro_estimado: 2300,
            configuracion: {
              radio_km: 10,
              max_paradas: 3,
              preferencia: "MENOR_PRECIO",
              por_defecto_aplicado: [],
            },
            asignaciones: [],
            items_no_asignados: [],
            ruteo: { distancia_total_km: 0, paradas: [] },
            mensaje: null,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/v1/compras-guiadas/7")) {
        return new Response(
          JSON.stringify({
            id: 7,
            carrito_distribuido_id: 20,
            fecha_inicio: "2026-06-15T12:10:00",
            fecha_cierre: null,
            estado_cierre: null,
            paradas: [
              {
                orden: 1,
                sucursal_id: 101,
                sucursal: "Día Av. Rivadavia",
                comercio: "Supermercado Día",
                direccion: "Av. Rivadavia 4500",
                localidad: "Córdoba",
                provincia: "Córdoba",
                distancia_desde_anterior_km: 1.2,
                bandera_nombre: "Día",
                bandera_logo_url: null,
                subtotal: 2500,
                items: [
                  {
                    progreso_item_id: 301,
                    item_asignado_id: 201,
                    item_carrito_id: 1,
                    producto_id: 1,
                    nombre_producto: "Leche Entera Larga Vida",
                    cantidad: 2,
                    precio_unitario: 1250,
                    subtotal: 2500,
                    url_imagen: null,
                    estado: "PENDIENTE",
                  },
                ],
              },
            ],
          }),
          { status: 200 },
        );
      }

      if (
        url.includes("/api/v1/carritos") &&
        !url.includes("/activo") &&
        !url.includes("/distribuir")
      ) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 10,
                titulo: "Mi Compra Semanal",
                activo: true,
                cantidad_items: 15,
                fecha_ultima_edicion: "2026-06-15T10:30:00",
              },
            ],
            total: 1,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/v1/productos/")) {
        return new Response(
          JSON.stringify({
            producto: {
              id: 1,
              codigo_ean: "7790742300101",
              nombre: "Leche Entera Larga Vida",
              marca: "La Serenísima",
              presentacion: "1 Litro",
              url_imagen: null,
            },
            precios: [],
            filtro_radio_activo: false,
            mensaje: null,
          }),
          { status: 200 },
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    }),
  );
}

function renderRoute(
  initialEntry: string,
  { authenticated = false }: { authenticated?: boolean } = {},
) {
  const state = authenticated
    ? {
        token: "valid-token",
        usuario: { id: 1, nombre: "Ana", correo: "ana@test.com" },
      }
    : { token: null, usuario: null };

  useAuthStore.setState(state);

  const router = createMemoryRouter(routes, { initialEntries: [initialEntry] });

  render(
    <Providers>
      <RouterProvider router={router} />
    </Providers>,
  );

  return router;
}

describe("Routing integration", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    useAuthStore.setState({ token: null, usuario: null });
  });

  it("renders the home route", () => {
    renderRoute("/");
    expect(screen.getByRole("heading", { name: /carrito sin título/i })).toBeInTheDocument();
  });

  it("hides private nav links when the user is not authenticated", () => {
    renderRoute("/");
    expect(screen.queryByRole("link", { name: /mis carritos/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /perfil/i })).not.toBeInTheDocument();
  });

  it("shows private nav links when the user is authenticated", () => {
    mockBackendResponses();
    renderRoute("/", { authenticated: true });
    expect(screen.getByRole("link", { name: /mis carritos/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /perfil/i })).toBeInTheDocument();
  });

  it("renders the login route", () => {
    renderRoute("/login");
    expect(screen.getByRole("heading", { name: /iniciar sesión/i })).toBeInTheDocument();
  });

  it("renders the registro route", () => {
    renderRoute("/registro");
    expect(screen.getByRole("heading", { name: /crear cuenta/i })).toBeInTheDocument();
  });

  it("renders the password recovery route", () => {
    renderRoute("/recuperar");
    expect(screen.getByRole("heading", { name: /recuperar contraseña/i })).toBeInTheDocument();
  });

  it("renders the public product detail route for anonymous users", async () => {
    mockBackendResponses();
    renderRoute("/productos/1");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /leche entera larga vida/i })).toBeInTheDocument();
    });
  });

  it("redirects /carrito to the home route", async () => {
    renderRoute("/carrito");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /carrito sin título/i })).toBeInTheDocument();
    });
  });

  it("renders /perfil when the user is authenticated", async () => {
    mockBackendResponses();
    renderRoute("/perfil", { authenticated: true });
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /mi perfil/i })).toBeInTheDocument();
    });
  });

  it.each([
    ["/carritos", /mis carritos/i],
    ["/distribucion", /tu ruta de ahorro está lista/i],
    ["/compra-guiada/7", /compra guiada/i],
  ])("renders %s when the user is authenticated", async (path, heading) => {
    mockBackendResponses();
    renderRoute(path, { authenticated: true });
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    });
    if (path === "/distribucion") {
      await waitFor(() => {
        expect(screen.getByText(/subtotal/i)).toBeInTheDocument();
      });
    }
    if (path === "/carritos") {
      await waitFor(() => {
        expect(screen.getByText(/activo/i)).toBeInTheDocument();
      });
    }
  });

  it.each(["/perfil", "/carritos", "/distribucion", "/compra-guiada/7"])(
    "redirects unauthenticated users from %s to /login",
    async (path) => {
      renderRoute(path);
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /iniciar sesión/i })).toBeInTheDocument();
      });
    },
  );

  it("redirects /old to the home route", async () => {
    renderRoute("/old");
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /home/i })).toHaveAttribute("href", "/");
    });
  });

  it("renders the not found page for unknown routes", () => {
    renderRoute("/ruta-inexistente");
    expect(screen.getByText(/404 - página no encontrada/i)).toBeInTheDocument();
  });
});
