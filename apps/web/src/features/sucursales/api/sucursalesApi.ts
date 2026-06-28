import { getSucursales, type SucursalMapa } from "@/lib/api";

export type { SucursalMapa };

export interface ObtenerSucursalesParams {
  lat: number;
  lon: number;
  radioKm: number;
}

export function obtenerSucursales({
  lat,
  lon,
  radioKm,
}: ObtenerSucursalesParams): Promise<SucursalMapa[]> {
  return getSucursales(lat, lon, radioKm);
}
