import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EstadoItem } from "@tfg/shared";

import { finalizarCompraGuiada, getCompraGuiada, updateProgresoItem } from "@/lib/api";
import type { CompraGuiadaResponse } from "@/lib/api";
import { useAppStore } from "@/store/appStore";
import { useToastStore } from "@/store/toastStore";

import { buildCompraGuiada } from "../lib/buildCompraGuiada";
import { compraGuiadaQueryKeys } from "../lib/queryKeys";

export function useCompraGuiadaViewModel(
  compraId: number | null,
  onFinalizado?: () => void,
) {
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);
  const setCompraGuiadaActiva = useAppStore((state) => state.setCompraGuiadaActiva);

  const query = useQuery({
    queryKey: compraId == null ? compraGuiadaQueryKeys.all : compraGuiadaQueryKeys.detail(compraId),
    queryFn: () => {
      if (compraId == null) throw new Error("Compra guiada inválida.");
      return getCompraGuiada(compraId);
    },
    enabled: compraId != null,
    staleTime: 0,
    retry: 1,
  });

  const actualizarMutation = useMutation({
    mutationFn: ({
      progresoItemId,
      estado,
    }: {
      progresoItemId: number;
      estado: EstadoItem;
    }) => {
      if (compraId == null) throw new Error("Compra guiada inválida.");
      return updateProgresoItem(compraId, progresoItemId, estado);
    },
    onMutate: async ({ progresoItemId, estado }) => {
      if (compraId == null) return undefined;
      const queryKey = compraGuiadaQueryKeys.detail(compraId);
      await queryClient.cancelQueries({ queryKey });
      const anterior = queryClient.getQueryData<CompraGuiadaResponse>(queryKey);
      queryClient.setQueryData<CompraGuiadaResponse>(queryKey, (actual) =>
        actual ? aplicarEstadoOptimista(actual, progresoItemId, estado) : actual,
      );
      return { anterior };
    },
    onError: (_error, _variables, context) => {
      if (compraId == null || !context?.anterior) return;
      queryClient.setQueryData(compraGuiadaQueryKeys.detail(compraId), context.anterior);
    },
    onSuccess: (compra) => {
      queryClient.setQueryData(compraGuiadaQueryKeys.detail(compra.id), compra);
    },
  });

  const finalizarMutation = useMutation<CompraGuiadaResponse, Error, boolean>({
    mutationFn: (confirmarInterrupcion) => {
      if (compraId == null) throw new Error("Compra guiada inválida.");
      return finalizarCompraGuiada(compraId, confirmarInterrupcion);
    },
    onSuccess: (compra) => {
      queryClient.setQueryData(compraGuiadaQueryKeys.detail(compra.id), compra);
      setCompraGuiadaActiva(null);
      const completada = compra.estado_cierre === "COMPLETADA";
      addToast({
        message: completada
          ? "Compra finalizada con éxito."
          : "Compra interrumpida.",
        variant: completada ? "success" : "warning",
      });
      onFinalizado?.();
    },
    onError: () => {
      addToast({
        message: "No se pudo finalizar la compra. Intentá nuevamente.",
        variant: "error",
      });
    },
  });

  const compra = useMemo(() => {
    if (!query.data) return null;
    return buildCompraGuiada(query.data);
  }, [query.data]);

  const totalItems = compra?.totalItems ?? 0;
  const pendientes = useMemo(() => {
    if (!compra) return 0;
    return compra.paradas.reduce(
      (total, parada) =>
        total + parada.items.filter((item) => item.estado === EstadoItem.PENDIENTE).length,
      0,
    );
  }, [compra]);

  function actualizarEstado(progresoItemId: number, estado: EstadoItem): void {
    actualizarMutation.mutate({ progresoItemId, estado });
  }

  return {
    compra,
    query,
    totalItems,
    resueltos: totalItems - pendientes,
    pendientes,
    progreso: totalItems > 0 ? ((totalItems - pendientes) / totalItems) * 100 : 0,
    actualizarEstado,
    finalizar: (confirmarInterrupcion = false) => finalizarMutation.mutate(confirmarInterrupcion),
    finalizando: finalizarMutation.isPending,
  };
}

function aplicarEstadoOptimista(
  compra: CompraGuiadaResponse,
  progresoItemId: number,
  estado: EstadoItem,
): CompraGuiadaResponse {
  return {
    ...compra,
    paradas: compra.paradas.map((parada) => ({
      ...parada,
      items: parada.items.map((item) =>
        item.progreso_item_id === progresoItemId ? { ...item, estado } : item,
      ),
    })),
  };
}
