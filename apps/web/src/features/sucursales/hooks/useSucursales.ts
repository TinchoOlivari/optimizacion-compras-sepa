import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  obtenerSucursales,
  type SucursalMapa,
} from "@/features/sucursales/api/sucursalesApi";

import { sucursalesQueryKeys } from "../lib/queryKeys";

const STALE_TIME_MS = 60_000;

export function useSucursales(
  lat: number | undefined,
  lon: number | undefined,
  radioKm: number | undefined,
) {
  const enabled =
    lat !== undefined &&
    lon !== undefined &&
    radioKm !== undefined &&
    Number.isFinite(lat) &&
    Number.isFinite(lon) &&
    Number.isFinite(radioKm);

  return useQuery<SucursalMapa[], Error>({
    queryKey: sucursalesQueryKeys.cercanas(lat, lon, radioKm),
    queryFn: () =>
      obtenerSucursales({
        lat: lat ?? 0,
        lon: lon ?? 0,
        radioKm: radioKm ?? 10,
      }),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: STALE_TIME_MS,
    retry: 1,
  });
}
