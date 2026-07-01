import { EstadoItem } from "@tfg/shared";

import type { CompraGuiadaResponse, ItemCompraGuiadaResponse } from "@/lib/api";

export interface ItemCompraViewModel {
  progresoItemId: number;
  itemCarritoId: number;
  productoId: number;
  nombre: string;
  cantidad: number;
  precioUnitario: number;
  subtotal: number;
  urlImagen: string | null;
  estado: EstadoItem;
}

export interface ParadaCompraViewModel {
  numero: number;
  sucursalId: number;
  sucursal: string;
  comercio: string;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  distanciaKm: number | null;
  banderaNombre: string | null;
  banderaLogoUrl: string | null;
  subtotal: number;
  esAdicional: boolean;
  items: ItemCompraViewModel[];
}

export interface CompraGuiadaViewModel {
  paradas: ParadaCompraViewModel[];
  totalItems: number;
}

export function buildCompraGuiada(compra: CompraGuiadaResponse): CompraGuiadaViewModel {
  const paradas = compra.paradas.map((parada, index) => ({
    numero: index + 1,
    sucursalId: parada.sucursal_id,
    sucursal: parada.sucursal,
    comercio: parada.comercio,
    direccion: parada.direccion,
    localidad: parada.localidad,
    provincia: parada.provincia,
    distanciaKm: parada.distancia_desde_anterior_km,
    banderaNombre: parada.bandera_nombre,
    banderaLogoUrl: parada.bandera_logo_url,
    subtotal: parada.subtotal,
    esAdicional: parada.es_adicional,
    items: parada.items.map(buildItemCompra),
  }));

  return {
    paradas,
    totalItems: paradas.reduce((total, parada) => total + parada.items.length, 0),
  };
}

function buildItemCompra(item: ItemCompraGuiadaResponse): ItemCompraViewModel {
  return {
    progresoItemId: item.progreso_item_id,
    itemCarritoId: item.item_carrito_id,
    productoId: item.producto_id,
    nombre: item.nombre_producto,
    cantidad: item.cantidad,
    precioUnitario: item.precio_unitario,
    subtotal: item.subtotal,
    urlImagen: item.url_imagen,
    estado: item.estado ?? EstadoItem.PENDIENTE,
  };
}

export function formatearDireccionParada(
  parada: Pick<ParadaCompraViewModel, "direccion" | "localidad" | "provincia">,
): string {
  return [parada.direccion, parada.localidad, parada.provincia].filter(Boolean).join(", ");
}
