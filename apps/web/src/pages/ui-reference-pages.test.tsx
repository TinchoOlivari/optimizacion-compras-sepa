import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type React from "react";

import { Providers } from "@/components/Providers";
import CarritosGuardadosPage from "@/pages/CarritosGuardados";
import CompraGuiadaPage from "@/pages/CompraGuiada";
import PerfilPage from "@/pages/Perfil";
import ProductoDetallePage from "@/pages/ProductoDetalle";
import RecuperarPasswordPage from "@/pages/RecuperarPassword";
import ResultadoDistribucionPage from "@/pages/ResultadoDistribucion";
import { useAuthStore } from "@/store/authStore";

function renderWithProviders(ui: React.ReactElement, initialEntry = "/") {
  render(
    <Providers>
      <MemoryRouter initialEntries={[initialEntry]}>{ui}</MemoryRouter>
    </Providers>,
  );
}

const PRODUCTO_DETALLE_FIXTURE = {
  producto: {
    id: 1,
    codigo_ean: "7790742300101",
    nombre: "Leche Entera Larga Vida",
    marca: "La Serenísima",
    presentacion: "1 Litro",
    url_imagen: null,
  },
  precios: [
    {
      comercio_id: 1,
      comercio: "Supermercado Día",
      sucursal_id: 101,
      sucursal: "Día Av. Rivadavia",
      direccion: "Av. Rivadavia 4500",
      localidad: "Córdoba",
      provincia: "Córdoba",
      precio: 1250,
      fecha_vigencia: "2026-06-14",
      distancia_km: 1.2,
      precio_minimo: true,
    },
  ],
  filtro_radio_activo: false,
  mensaje: null,
};

const CARRITOS_FIXTURE = {
  items: [
    {
      id: 10,
      titulo: "Mi Compra Semanal",
      activo: true,
      cantidad_items: 15,
      fecha_ultima_edicion: "2026-06-15T10:30:00",
    },
    {
      id: 11,
      titulo: "Asado Domingo",
      activo: false,
      cantidad_items: 8,
      fecha_ultima_edicion: "2026-06-14T18:45:00",
    },
    {
      id: 12,
      titulo: "12 de octubre",
      activo: false,
      cantidad_items: 24,
      fecha_ultima_edicion: "2023-10-12T12:00:00",
    },
  ],
  total: 3,
};

const CARRITO_ACTIVO_FIXTURE = {
  id: 10,
  titulo: "Mi Compra Semanal",
  activo: true,
  items: [],
};

const DISTRIBUCION_FIXTURE = {
  id: 20,
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
      items: [
        {
          item_carrito_id: 1,
          producto_id: 1,
          nombre_producto: "Leche Entera Larga Vida",
          cantidad: 2,
          precio_unitario: 1250,
          subtotal: 2500,
          url_imagen: null,
        },
      ],
      direccion: "Av. Rivadavia 4500",
      localidad: "Córdoba",
      provincia: "Córdoba",
      latitud: -31.4175,
      longitud: -64.1833,
      distancia_km: 1.2,
      bandera_nombre: "Día",
      bandera_logo_url: null,
    },
  ],
  items_no_asignados: [],
  ruteo: {
    distancia_total_km: 2.4,
    paradas: [],
  },
  mensaje: null,
};

const COMPRA_GUIADA_FIXTURE = {
  id: 30,
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
      subtotal: 8500,
      es_adicional: false,
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
};

function mockFetch(handler: (url: string, init?: RequestInit) => unknown | Promise<unknown>): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const body = await handler(url, init);
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
}

function mockPreferencias(): void {
  mockFetch((url) => {
    if (url.includes("/api/v1/preferencias")) {
      return {
        radio_km: 5,
        max_paradas: 3,
        preferencia: "MENOR_PRECIO",
        origen: { latitud: -31.4175, longitud: -64.1833 },
        por_defecto_aplicado: [],
      };
    }
    return {};
  });
}

describe("UI reference pages", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({
      token: "valid-token",
      usuario: { id: 1, nombre: "Usuario Test", correo: "test@example.com" },
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    useAuthStore.setState({ token: null, usuario: null });
  });

  it("renders product detail with summary, prices and CTA", async () => {
    mockFetch((url) => {
      if (url.includes("/api/v1/preferencias")) {
        return {
          radio_km: 5,
          max_paradas: 3,
          preferencia: "MENOR_PRECIO",
          origen: { latitud: -31.4175, longitud: -64.1833 },
          por_defecto_aplicado: [],
        };
      }
      if (url.includes("/api/v1/carritos/activo")) return CARRITO_ACTIVO_FIXTURE;
      if (url.includes("/api/v1/productos/1")) return PRODUCTO_DETALLE_FIXTURE;
      return {};
    });

    renderWithProviders(
      <Routes>
        <Route path="/productos/:id" element={<ProductoDetallePage />} />
      </Routes>,
      "/productos/1",
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /leche entera larga vida/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/ean: 7790742300101/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /precios disponibles/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /agregar al carrito/i })).toBeInTheDocument();
  });

  it("renders saved carts with management actions", async () => {
    mockFetch((url) => {
      if (
        url.includes("/api/v1/carritos") &&
        !url.includes("/activo") &&
        !url.includes("/distribuir")
      ) {
        return CARRITOS_FIXTURE;
      }
      return {};
    });

    renderWithProviders(<CarritosGuardadosPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /mis carritos/i })).toBeInTheDocument();
      expect(screen.getByText(/activo/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /crear carrito nuevo/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /seleccionar/i })).toHaveLength(2);
  });

  it("renders distribution result with economic summary and guided purchase CTA", async () => {
    mockFetch((url, init) => {
      if (url.includes("/distribucion")) return DISTRIBUCION_FIXTURE;
      if (url.includes("/api/v1/carritos/activo")) return CARRITO_ACTIVO_FIXTURE;
      if (url.includes("/distribuir") && init?.method === "POST") return DISTRIBUCION_FIXTURE;
      return {};
    });

    renderWithProviders(<ResultadoDistribucionPage />);

    await waitFor(() => {
      expect(screen.getByText(/^Subtotal$/i)).toBeInTheDocument();
    });
    expect(
      screen.getByRole("heading", { name: /tu ruta de ahorro está lista/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Ahorro estimado$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /comenzar recorrido/i })).toBeInTheDocument();
  });

  it("renders guided purchase grouped by stop and updates item status", async () => {
    mockFetch((url, init) => {
      if (url.includes("/api/v1/compras-guiadas/30/items/301") && init?.method === "PATCH") {
        return {
          compra: {
            ...COMPRA_GUIADA_FIXTURE,
            paradas: [
              {
                ...COMPRA_GUIADA_FIXTURE.paradas[0],
                items: [{ ...COMPRA_GUIADA_FIXTURE.paradas[0].items[0], estado: "CONSEGUIDO" }],
              },
            ],
          },
          resultado_alternativas: null,
          aplicado_automaticamente: false,
        };
      }
      if (url.includes("/api/v1/compras-guiadas/30")) return COMPRA_GUIADA_FIXTURE;
      return {};
    });

    renderWithProviders(
      <Routes>
        <Route path="/compra-guiada/:id" element={<CompraGuiadaPage />} />
      </Routes>,
      "/compra-guiada/30",
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /compra guiada/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/1 pendiente/i)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /marcar leche entera larga vida como conseguido/i }),
    );
    await waitFor(() => {
      expect(screen.getByText(/sin pendientes/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /finalizar compra/i })).toBeInTheDocument();
  });

  it("shows missing item alternatives when product is not found", async () => {
    mockFetch((url, init) => {
      if (url.includes("/api/v1/compras-guiadas/30/items/301") && init?.method === "PATCH") {
        return {
          compra: {
            ...COMPRA_GUIADA_FIXTURE,
            paradas: [
              {
                ...COMPRA_GUIADA_FIXTURE.paradas[0],
                items: [
                  { ...COMPRA_GUIADA_FIXTURE.paradas[0].items[0], estado: "NO_ENCONTRADO" },
                ],
              },
            ],
          },
          resultado_alternativas: {
            progreso_item_id: 301,
            tiene_alternativas: true,
            alternativas: [
              {
                tipo: "MISMO_PRODUCTO",
                precio_id: 901,
                producto_id: 1,
                nombre_producto: "Leche Entera Larga Vida",
                url_imagen: null,
                sucursal_id: 102,
                sucursal: "Día Nueva Córdoba",
                comercio: "Supermercado Día",
                direccion: "Bv. Illia 100",
                localidad: "Córdoba",
                provincia: "Córdoba",
                bandera_nombre: "Día",
                bandera_logo_url: null,
                precio_unitario: 1300,
                subtotal: 2600,
                diferencia_precio: 100,
                distancia_km: 1.8,
                esta_en_recorrido: false,
                requiere_nueva_parada: true,
                confianza: "ALTA",
                motivo: "Mismo producto en una sucursal cercana.",
              },
              {
                tipo: "MISMO_PRODUCTO",
                precio_id: 902,
                producto_id: 1,
                nombre_producto: "Leche Entera Larga Vida",
                url_imagen: null,
                sucursal_id: 103,
                sucursal: "Disco Centro",
                comercio: "Disco",
                direccion: "San Martín 50",
                localidad: "Córdoba",
                provincia: "Córdoba",
                bandera_nombre: null,
                bandera_logo_url: null,
                precio_unitario: 1220,
                subtotal: 2440,
                diferencia_precio: -60,
                distancia_km: 2.1,
                esta_en_recorrido: true,
                requiere_nueva_parada: false,
                confianza: "ALTA",
                motivo: "Mismo producto en una parada ya recomendada.",
              },
            ],
          },
          aplicado_automaticamente: false,
        };
      }
      if (url.includes("/api/v1/compras-guiadas/30")) return COMPRA_GUIADA_FIXTURE;
      return {};
    });

    renderWithProviders(
      <Routes>
        <Route path="/compra-guiada/:id" element={<CompraGuiadaPage />} />
      </Routes>,
      "/compra-guiada/30",
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /compra guiada/i })).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /marcar leche entera larga vida como no encontrado/i }),
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /resolver producto faltante/i })).toBeInTheDocument();
    });
    expect(screen.getAllByText(/leche entera larga vida/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/ya está en tu recorrido/i)).toBeInTheDocument();
    expect(screen.getByText(/requiere parada nueva/i)).toBeInTheDocument();
  });

  it("renders password recovery form with CTA and return link", () => {
    renderWithProviders(<RecuperarPasswordPage />);

    expect(screen.getByRole("heading", { name: /recuperar contraseña/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enviar enlace/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /volver/i })).toHaveAttribute("href", "/login");
  });

  it("renders redesigned profile with radios, user card and logout", async () => {
    mockPreferencias();

    renderWithProviders(<PerfilPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /mi perfil/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/usuario test/i)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /menor precio/i })).toBeChecked();
    expect(screen.getByRole("button", { name: /guardar preferencias/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cerrar sesión/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/latitud/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/longitud/i)).not.toBeInTheDocument();
  });
});
