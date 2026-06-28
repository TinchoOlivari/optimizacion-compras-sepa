import { EstadoItem } from "@tfg/shared";

export interface CompraGuiadaItem {
  productoId: number;
  nombre: string;
  cantidad: number;
  precioUnitario: number;
  estado: EstadoItem;
}

export interface ParadaCompraGuiada {
  numero: number;
  comercio: string;
  sucursal: string;
  direccion: string;
  items: CompraGuiadaItem[];
}

export interface CompraGuiadaMock {
  id: number;
  paradas: ParadaCompraGuiada[];
}

const MOCK_ASIGNACIONES = [
  {
    sucursalId: 101,
    comercio: "Supermercado Día",
    sucursal: "Día Av. Rivadavia",
    direccion: "Av. Rivadavia 4500",
    items: [
      { productoId: 1, nombre: "Leche Entera Larga Vida", cantidad: 2, precioUnitario: 1250 },
      { productoId: 2, nombre: "Café Molido Cabrales", cantidad: 1, precioUnitario: 6000 },
    ],
  },
  {
    sucursalId: 202,
    comercio: "Carrefour Express",
    sucursal: "Carrefour Av. Acoyte",
    direccion: "Av. Acoyte 120",
    items: [{ productoId: 3, nombre: "Pan Lactal Blanco", cantidad: 1, precioUnitario: 6000 }],
  },
];

export const compraGuiadaMock: CompraGuiadaMock = {
  id: 7,
  paradas: MOCK_ASIGNACIONES.map((asignacion, index) => ({
    numero: index + 1,
    comercio: asignacion.comercio,
    sucursal: asignacion.sucursal,
    direccion: asignacion.direccion,
    items: asignacion.items.map((item) => ({ ...item, estado: EstadoItem.PENDIENTE })),
  })),
};
