import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { CarritoDetalle } from "@tfg/shared";

import {
  addItem as addItemAnonimo,
  clearCarritoAnonimo,
  removeItem as removeItemAnonimo,
  setItemQuantity as setItemQuantityAnonimo,
} from "@/lib/carrito-anonimo";
import {
  addItem,
  createCarrito,
  getCarritoDetalle,
  removeItem,
  updateItem,
} from "@/lib/api";
import { useToastStore } from "@/store/toastStore";

import {
  handleCarritoDomainEvent,
  invalidateCarritoLista,
} from "../lib/cachePolicy";
import { carritoQueryKeys } from "../lib/queryKeys";

export interface UseCarritoMutationsOptions {
  autenticado: boolean;
  carritoActivo?: CarritoDetalle | null;
  onAnonimoChange?: () => void;
  onTokenExpirado?: () => void;
}

export function useCarritoMutations({
  autenticado,
  carritoActivo,
  onAnonimoChange,
  onTokenExpirado,
}: UseCarritoMutationsOptions) {
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);

  async function onAuthMutationSuccess(
    event: "items_changed",
  ): Promise<void> {
    if (autenticado) {
      await handleCarritoDomainEvent(queryClient, event);
      return;
    }
    onAnonimoChange?.();
  }

  function onAuthMutationError(error: Error, message: string): void {
    if (error.message.includes("401") || error.message.includes("403")) {
      onTokenExpirado?.();
    }
    addToast({ message, variant: "error" });
  }

  async function resolveCarritoActivoId(): Promise<number> {
    const cached = queryClient.getQueryData<CarritoDetalle | null>(carritoQueryKeys.activo());
    if (cached?.id) {
      return cached.id;
    }

    const existente = await getCarritoDetalle();
    if (existente?.id) {
      queryClient.setQueryData(carritoQueryKeys.activo(), existente);
      return existente.id;
    }

    const creado = await createCarrito();
    const carrito: CarritoDetalle = {
      id: creado.id,
      titulo: creado.titulo,
      activo: creado.activo,
      items: [],
    };
    queryClient.setQueryData(carritoQueryKeys.activo(), carrito);
    await invalidateCarritoLista(queryClient);
    return carrito.id;
  }

  async function resolveCarritoActivoIdExistente(): Promise<number> {
    if (carritoActivo?.id) {
      return carritoActivo.id;
    }

    const cached = queryClient.getQueryData<CarritoDetalle | null>(carritoQueryKeys.activo());
    if (cached?.id) {
      return cached.id;
    }

    const existente = await getCarritoDetalle();
    if (existente?.id) {
      queryClient.setQueryData(carritoQueryKeys.activo(), existente);
      return existente.id;
    }

    throw new Error("No hay un carrito activo disponible.");
  }

  const addItemMutation = useMutation<
    unknown,
    Error,
    { productoId: number; cantidad: number }
  >({
    mutationFn: async ({ productoId, cantidad }) => {
      if (autenticado) {
        const carritoId = await resolveCarritoActivoId();
        return addItem(carritoId, { producto_id: productoId, cantidad });
      }
      return addItemAnonimo(productoId, cantidad);
    },
    onSuccess: async () => {
      await onAuthMutationSuccess("items_changed");
      addToast({ message: "Producto agregado al carrito.", variant: "success" });
    },
    onError: (error) => {
      onAuthMutationError(error, "No pudimos agregar el producto al carrito.");
    },
  });

  const updateItemMutation = useMutation<
    unknown,
    Error,
    { productoId: number; cantidad: number; itemId?: number }
  >({
    mutationFn: async ({ productoId, cantidad, itemId }) => {
      if (autenticado && itemId !== undefined) {
        const carritoId = await resolveCarritoActivoIdExistente();
        return updateItem(carritoId, itemId, { cantidad });
      }
      return setItemQuantityAnonimo(productoId, cantidad);
    },
    onSuccess: async () => {
      await onAuthMutationSuccess("items_changed");
    },
    onError: (error) => {
      onAuthMutationError(error, "No pudimos actualizar la cantidad.");
    },
  });

  const removeItemMutation = useMutation<
    unknown,
    Error,
    { productoId: number; itemId?: number }
  >({
    mutationFn: async ({ productoId, itemId }) => {
      if (autenticado && itemId !== undefined) {
        const carritoId = await resolveCarritoActivoIdExistente();
        return removeItem(carritoId, itemId);
      }
      return removeItemAnonimo(productoId);
    },
    onSuccess: async () => {
      await onAuthMutationSuccess("items_changed");
      addToast({ message: "Producto eliminado del carrito.", variant: "success" });
    },
    onError: (error) => {
      onAuthMutationError(error, "No pudimos eliminar el producto del carrito.");
    },
  });

  const vaciarCarritoMutation = useMutation<unknown, Error>({
    mutationFn: async () => {
      if (autenticado) {
        const carritoId = await resolveCarritoActivoIdExistente();
        const cached = queryClient.getQueryData<CarritoDetalle | null>(carritoQueryKeys.activo());
        const items = carritoActivo?.items ?? cached?.items ?? [];
        if (items.length === 0) {
          throw new Error("No hay productos para quitar.");
        }
        await Promise.all(items.map((item) => removeItem(carritoId, item.id)));
        return;
      }
      clearCarritoAnonimo();
    },
    onSuccess: async () => {
      await onAuthMutationSuccess("items_changed");
      addToast({ message: "Carrito vaciado.", variant: "success" });
    },
    onError: (error) => {
      onAuthMutationError(error, "No pudimos vaciar el carrito.");
    },
  });

  return {
    addItemMutation,
    updateItemMutation,
    removeItemMutation,
    vaciarCarritoMutation,
  };
}
