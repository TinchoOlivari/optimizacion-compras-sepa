export const preferenciasQueryKeys = {
  all: ["preferencias"] as const,
  actuales: () => ["preferencias", "actuales"] as const,
  geocodificacion: (direccion: string) =>
    ["preferencias", "geocodificacion", direccion] as const,
};
