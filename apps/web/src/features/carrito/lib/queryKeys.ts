export const carritoQueryKeys = {
  all: ["carritos"] as const,
  activo: () => ["carritos", "activo"] as const,
  lista: () => ["carritos", "lista"] as const,
  distribucion: () => ["carritos", "distribucion"] as const,
};
