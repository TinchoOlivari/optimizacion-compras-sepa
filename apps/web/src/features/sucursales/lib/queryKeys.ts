export const sucursalesQueryKeys = {
  all: ["sucursales"] as const,
  cercanas: (lat: number | undefined, lon: number | undefined, radioKm: number | undefined) =>
    ["sucursales", "cercanas", lat, lon, radioKm] as const,
};
