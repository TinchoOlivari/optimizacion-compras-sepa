import { EstadoItem, type EstadoCierre } from "@tfg/shared";
import type {
  Carrito,
  CarritoDetalle,
  ItemCarrito,
  PrecioProducto,
  ProductoResumen,
} from "@tfg/shared";

import { useAuthStore } from "@/store/authStore";

export const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, path: string, body: unknown) {
    super(`API error ${status} en ${path}`);
    this.status = status;
    this.body = body;
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? undefined);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = useAuthStore.getState().token;
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    useAuthStore.getState().logout();
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new ApiError(response.status, path, body);
  }

  return body as T;
}

export interface HealthResponse {
  status: string;
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/health");
}

export interface UbicacionReferencia {
  latitud: number;
  longitud: number;
  direccion?: string | null;
  modalidad?: string | null;
}

export interface PreferenciasResponse {
  radio_km: number;
  max_paradas: number;
  preferencia: string;
  origen: {
    latitud: number;
    longitud: number;
    direccion?: string | null;
    modalidad?: string | null;
  };
  por_defecto_aplicado: string[];
}

export function getPreferencias(): Promise<PreferenciasResponse> {
  return apiFetch<PreferenciasResponse>("/api/v1/preferencias");
}

export function updatePreferencias(payload: {
  radio_km: number;
  max_paradas: number;
  modo_preferencia: string;
  ubicacion_referencia: UbicacionReferencia;
}): Promise<PreferenciasResponse> {
  return apiFetch<PreferenciasResponse>("/api/v1/preferencias", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

interface BuscarProductosResponse {
  items: ProductoResumen[];
  total: number;
}

export interface ProductoDetalleResponse {
  producto: ProductoResumen;
  precios: PrecioProducto[];
  filtro_radio_activo: boolean;
  mensaje: string | null;
}

interface SucursalGeoResponse {
  id: number;
  nombre: string | null;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  latitud: number;
  longitud: number;
  distancia_km: number | null;
  comercio_id: number;
  comercio_marca: string | null;
  bandera_nombre: string | null;
  bandera_logo_url: string | null;
}

export interface SucursalMapa {
  id: number;
  nombre: string | null;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  latitud: number;
  longitud: number;
  distanciaKm: number | null;
  comercioId: number;
  comercioMarca: string | null;
  banderaNombre: string | null;
  banderaLogoUrl: string | null;
}

interface CarritosResponse {
  items: Carrito[];
  total: number;
}

interface CrearCarritoResponse {
  id: number;
  titulo: string | null;
  activo: boolean;
  items: ItemCarrito[];
}

interface ActualizarCarritoPayload {
  titulo?: string;
  activo?: boolean;
}

interface UpdateItemPayload {
  cantidad: number;
}

export function buscarProductos(q: string, limit = 5): Promise<BuscarProductosResponse> {
  const query = new URLSearchParams({ q, limit: String(limit) }).toString();
  return apiFetch<BuscarProductosResponse>(`/api/v1/productos/buscar?${query}`);
}

export function getProductoDetalle(
  productoId: number,
  filtros?: { lat: number; lon: number; radio_km: number },
): Promise<ProductoDetalleResponse> {
  const query = filtros
    ? `?${new URLSearchParams({
        lat: String(filtros.lat),
        lon: String(filtros.lon),
        radio_km: String(filtros.radio_km),
      }).toString()}`
    : "";
  return apiFetch<ProductoDetalleResponse>(`/api/v1/productos/${productoId}${query}`);
}

export async function getSucursales(
  lat: number,
  lon: number,
  radioKm: number,
): Promise<SucursalMapa[]> {
  const query = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radio_km: String(radioKm),
  }).toString();
  const sucursales = await apiFetch<SucursalGeoResponse[]>(`/api/v1/sucursales?${query}`);
  return sucursales.map(toSucursalMapa);
}

function toSucursalMapa(sucursal: SucursalGeoResponse): SucursalMapa {
  return {
    id: sucursal.id,
    nombre: sucursal.nombre,
    direccion: sucursal.direccion,
    localidad: sucursal.localidad,
    provincia: sucursal.provincia,
    latitud: sucursal.latitud,
    longitud: sucursal.longitud,
    distanciaKm: sucursal.distancia_km,
    comercioId: sucursal.comercio_id,
    comercioMarca: sucursal.comercio_marca,
    banderaNombre: sucursal.bandera_nombre,
    banderaLogoUrl: sucursal.bandera_logo_url,
  };
}

export async function getCarritoDetalle(): Promise<CarritoDetalle | null> {
  try {
    return await apiFetch<CarritoDetalle>("/api/v1/carritos/activo");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function getCarritos(): Promise<CarritosResponse> {
  return apiFetch<CarritosResponse>("/api/v1/carritos");
}

export function createCarrito(): Promise<CrearCarritoResponse> {
  return apiFetch<CrearCarritoResponse>("/api/v1/carritos", { method: "POST" });
}

export function updateCarrito(
  carritoId: number,
  payload: ActualizarCarritoPayload,
): Promise<Carrito> {
  return apiFetch<Carrito>(`/api/v1/carritos/${carritoId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteCarrito(carritoId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/carritos/${carritoId}`, {
    method: "DELETE",
  });
}

export function addItem(
  carritoId: number,
  payload: { producto_id: number; cantidad: number },
): Promise<ItemCarrito> {
  return apiFetch<ItemCarrito>(`/api/v1/carritos/${carritoId}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateItem(
  carritoId: number,
  itemId: number,
  payload: UpdateItemPayload,
): Promise<ItemCarrito> {
  return apiFetch<ItemCarrito>(`/api/v1/carritos/${carritoId}/items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function removeItem(carritoId: number, itemId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/carritos/${carritoId}/items/${itemId}`, {
    method: "DELETE",
  });
}

export interface ItemAsignadoDistribucionResponse {
  item_carrito_id: number;
  producto_id: number;
  nombre_producto: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
  url_imagen: string | null;
}

export interface AsignacionSucursalDistribucionResponse {
  sucursal_id: number;
  sucursal: string;
  comercio: string;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  latitud: number;
  longitud: number;
  distancia_km: number | null;
  bandera_nombre: string | null;
  bandera_logo_url: string | null;
  subtotal: number;
  items: ItemAsignadoDistribucionResponse[];
}

export interface ItemNoAsignadoResponse {
  item_carrito_id: number;
  producto_id: number;
  nombre_producto: string;
  cantidad: number;
  url_imagen: string | null;
}

export interface ParadaRuteoResponse {
  orden: number;
  sucursal_id: number | null;
  nombre: string;
  distancia_desde_anterior_km: number;
  es_origen: boolean;
  es_adicional: boolean;
  productos: string[];
}

export interface CarritoDistribuidoResponse {
  id: number | null;
  fecha_calculo: string;
  costo_total_estimado: number;
  ahorro_estimado: number | null;
  configuracion: {
    radio_km: number;
    max_paradas: number;
    preferencia: string;
    por_defecto_aplicado: string[];
  };
  asignaciones: AsignacionSucursalDistribucionResponse[];
  items_no_asignados: ItemNoAsignadoResponse[];
  ruteo: {
    distancia_total_km: number;
    paradas: ParadaRuteoResponse[];
  };
  mensaje: string | null;
}

export interface DistribuirCarritoPayload {
  radio_km?: number;
  max_paradas?: number;
  preferencia?: string;
  ubicacion_referencia?: {
    latitud: number;
    longitud: number;
    direccion?: string;
    modalidad?: string;
  };
}

export function distribuirCarrito(
  carritoId: number,
  payload?: DistribuirCarritoPayload,
): Promise<CarritoDistribuidoResponse> {
  return apiFetch<CarritoDistribuidoResponse>(`/api/v1/carritos/${carritoId}/distribuir`, {
    method: "POST",
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export function getDistribucionVigente(carritoId: number): Promise<CarritoDistribuidoResponse> {
  return apiFetch<CarritoDistribuidoResponse>(`/api/v1/carritos/${carritoId}/distribucion`);
}

export interface ItemCompraGuiadaResponse {
  progreso_item_id: number;
  item_asignado_id: number;
  item_carrito_id: number;
  producto_id: number;
  nombre_producto: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
  url_imagen: string | null;
  estado: EstadoItem;
}

export interface ParadaCompraGuiadaResponse {
  orden: number;
  sucursal_id: number;
  sucursal: string;
  comercio: string;
  direccion: string | null;
  localidad: string | null;
  provincia: string | null;
  distancia_desde_anterior_km: number;
  bandera_nombre: string | null;
  bandera_logo_url: string | null;
  subtotal: number;
  items: ItemCompraGuiadaResponse[];
}

export interface CompraGuiadaResponse {
  id: number;
  carrito_distribuido_id: number;
  fecha_inicio: string;
  fecha_cierre: string | null;
  estado_cierre: EstadoCierre | null;
  paradas: ParadaCompraGuiadaResponse[];
}

export function iniciarCompraGuiada(carritoDistribuidoId: number): Promise<CompraGuiadaResponse> {
  return apiFetch<CompraGuiadaResponse>("/api/v1/compras-guiadas", {
    method: "POST",
    body: JSON.stringify({ carrito_distribuido_id: carritoDistribuidoId }),
  });
}

export function getCompraGuiada(compraId: number): Promise<CompraGuiadaResponse> {
  return apiFetch<CompraGuiadaResponse>(`/api/v1/compras-guiadas/${compraId}`);
}

export function updateProgresoItem(
  compraId: number,
  progresoItemId: number,
  estado: EstadoItem,
): Promise<CompraGuiadaResponse> {
  return apiFetch<CompraGuiadaResponse>(
    `/api/v1/compras-guiadas/${compraId}/items/${progresoItemId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ estado }),
    },
  );
}

export function finalizarCompraGuiada(
  compraId: number,
  confirmarInterrupcion = false,
): Promise<CompraGuiadaResponse> {
  return apiFetch<CompraGuiadaResponse>(`/api/v1/compras-guiadas/${compraId}/finalizar`, {
    method: "POST",
    body: JSON.stringify({ confirmar_interrupcion: confirmarInterrupcion }),
  });
}

export interface AuthApiResponse {
  usuario: { id: number; nombre: string; correo: string };
  token: string;
}

export interface RegistroPayload {
  nombre: string;
  correo: string;
  password: string;
  carritoAnonimo: { productoId: number; cantidad: number }[];
}

export function registrarUsuario(payload: RegistroPayload): Promise<AuthApiResponse> {
  return apiFetch<AuthApiResponse>("/api/v1/auth/registro", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface LoginPayload {
  correo: string;
  password: string;
  carritoAnonimo: { productoId: number; cantidad: number }[];
}

export function iniciarSesion(payload: LoginPayload): Promise<AuthApiResponse> {
  return apiFetch<AuthApiResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function solicitarRecuperacion(correo: string): Promise<{ mensaje: string }> {
  return apiFetch<{ mensaje: string }>("/api/v1/auth/recuperar", {
    method: "POST",
    body: JSON.stringify({ correo }),
  });
}

export function restablecerPassword(payload: {
  token: string;
  nuevaPassword: string;
}): Promise<AuthApiResponse> {
  return apiFetch<AuthApiResponse>("/api/v1/auth/restablecer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface ActualizarNombreResponse {
  id: number;
  nombre: string;
  correo: string;
}

export function actualizarNombre(nombre: string): Promise<ActualizarNombreResponse> {
  return apiFetch<ActualizarNombreResponse>("/api/v1/auth/perfil", {
    method: "PATCH",
    body: JSON.stringify({ nombre }),
  });
}
