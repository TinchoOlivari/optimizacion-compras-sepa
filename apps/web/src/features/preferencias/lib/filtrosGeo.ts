import type { PreferenciasResponse } from "@/lib/api";

import { VALORES_INICIALES_FORM } from "./form";

export interface FiltrosGeo {
  lat: number;
  lon: number;
  radio_km: number;
}

export function filtrosGeoPorDefecto(): FiltrosGeo {
  return {
    lat: VALORES_INICIALES_FORM.latitud,
    lon: VALORES_INICIALES_FORM.longitud,
    radio_km: VALORES_INICIALES_FORM.radio_km,
  };
}

export function filtrosGeoDesdePreferencias(
  preferencias: PreferenciasResponse | undefined,
): FiltrosGeo | undefined {
  if (!preferencias) return undefined;
  return {
    lat: preferencias.origen.latitud,
    lon: preferencias.origen.longitud,
    radio_km: preferencias.radio_km,
  };
}

export function filtrosGeoParaDetalleProducto(
  preferencias: PreferenciasResponse | undefined,
): FiltrosGeo {
  return filtrosGeoDesdePreferencias(preferencias) ?? filtrosGeoPorDefecto();
}
