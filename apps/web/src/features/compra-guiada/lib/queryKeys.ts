export const compraGuiadaQueryKeys = {
  all: ["compra-guiada"] as const,
  detail: (compraId: number) => ["compra-guiada", compraId] as const,
};
