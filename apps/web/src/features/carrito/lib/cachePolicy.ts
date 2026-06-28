import type { QueryClient } from "@tanstack/react-query";

import { carritoQueryKeys } from "./queryKeys";

export type CarritoDomainEvent =
  | "items_changed"
  | "carrito_deleted"
  | "carrito_activated"
  | "titulo_changed"
  | "session_changed";

type CarritoInvalidationEvent = Exclude<CarritoDomainEvent, "session_changed">;

const EVENT_INVALIDATE_QUERIES: Record<
  CarritoInvalidationEvent,
  readonly (() => readonly string[])[]
> = {
  items_changed: [carritoQueryKeys.activo, carritoQueryKeys.lista],
  carrito_deleted: [carritoQueryKeys.activo, carritoQueryKeys.lista],
  carrito_activated: [carritoQueryKeys.activo, carritoQueryKeys.lista],
  titulo_changed: [carritoQueryKeys.activo, carritoQueryKeys.lista],
};

const EVENTS_RESET_DISTRIBUCION = new Set<CarritoInvalidationEvent>([
  "items_changed",
  "carrito_deleted",
  "carrito_activated",
]);

export function resetCarritoCaches(queryClient: QueryClient): void {
  queryClient.removeQueries({ queryKey: carritoQueryKeys.all });
}

export async function invalidateCarritoLista(
  queryClient: QueryClient,
): Promise<void> {
  await queryClient.invalidateQueries({ queryKey: carritoQueryKeys.lista() });
}

export async function handleCarritoDomainEvent(
  queryClient: QueryClient,
  event: CarritoDomainEvent,
): Promise<void> {
  if (event === "session_changed") {
    resetCarritoCaches(queryClient);
    return;
  }

  const keyFns = EVENT_INVALIDATE_QUERIES[event];
  const tasks = keyFns.map((keyFn) =>
    queryClient.invalidateQueries({ queryKey: keyFn() }),
  );

  if (EVENTS_RESET_DISTRIBUCION.has(event)) {
    tasks.push(
      Promise.resolve(
        queryClient.removeQueries({ queryKey: carritoQueryKeys.distribucion() }),
      ),
    );
  }

  await Promise.all(tasks);
}
