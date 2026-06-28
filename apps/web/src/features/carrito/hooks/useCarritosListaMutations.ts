import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createCarrito, deleteCarrito, updateCarrito } from "@/lib/api";
import { useToastStore } from "@/store/toastStore";

import {
  handleCarritoDomainEvent,
} from "../lib/cachePolicy";

export interface UseCarritosListaMutationsOptions {
  onCarritoActivado?: () => void;
  onCarritoEliminado?: () => void;
}

export function useCarritosListaMutations({
  onCarritoActivado,
  onCarritoEliminado,
}: UseCarritosListaMutationsOptions = {}) {
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);

  const crearMutation = useMutation({
    mutationFn: createCarrito,
    onSuccess: async () => {
      await handleCarritoDomainEvent(queryClient, "carrito_activated");
      addToast({ message: "Carrito creado.", variant: "success" });
    },
    onError: () => {
      addToast({ message: "No pudimos crear el carrito.", variant: "error" });
    },
  });

  const activarMutation = useMutation({
    mutationFn: (carritoId: number) => updateCarrito(carritoId, { activo: true }),
    onSuccess: async () => {
      await handleCarritoDomainEvent(queryClient, "carrito_activated");
      addToast({ message: "Carrito activado.", variant: "success" });
      onCarritoActivado?.();
    },
    onError: () => {
      addToast({ message: "No pudimos activar el carrito.", variant: "error" });
    },
  });

  const renombrarMutation = useMutation({
    mutationFn: ({ carritoId, titulo }: { carritoId: number; titulo: string }) =>
      updateCarrito(carritoId, { titulo }),
    onSuccess: async () => {
      await handleCarritoDomainEvent(queryClient, "titulo_changed");
      addToast({ message: "Carrito renombrado.", variant: "success" });
    },
    onError: () => {
      addToast({ message: "No pudimos renombrar el carrito.", variant: "error" });
    },
  });

  const eliminarMutation = useMutation({
    mutationFn: (carritoId: number) => deleteCarrito(carritoId),
    onSuccess: async () => {
      await handleCarritoDomainEvent(queryClient, "carrito_deleted");
      addToast({ message: "Carrito eliminado.", variant: "success" });
      onCarritoEliminado?.();
    },
    onError: () => {
      addToast({ message: "No pudimos eliminar el carrito.", variant: "error" });
    },
  });

  return {
    crearMutation,
    activarMutation,
    renombrarMutation,
    eliminarMutation,
  };
}
