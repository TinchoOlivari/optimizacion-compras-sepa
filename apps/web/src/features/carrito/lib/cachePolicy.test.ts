import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import {
  handleCarritoDomainEvent,
  invalidateCarritoLista,
  resetCarritoCaches,
} from "./cachePolicy";
import { carritoQueryKeys } from "./queryKeys";

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe("cachePolicy", () => {
  it("invalida activo y lista, y elimina distribucion ante items_changed", async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const removeSpy = vi.spyOn(queryClient, "removeQueries");

    await handleCarritoDomainEvent(queryClient, "items_changed");

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.activo(),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.lista(),
    });
    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.distribucion(),
    });
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
    expect(removeSpy).toHaveBeenCalledTimes(1);
  });

  it("invalida activo y lista ante titulo_changed", async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await handleCarritoDomainEvent(queryClient, "titulo_changed");

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.activo(),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.lista(),
    });
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
  });

  it("resetea todo el dominio ante session_changed", async () => {
    const queryClient = createTestQueryClient();
    const removeSpy = vi.spyOn(queryClient, "removeQueries");

    await handleCarritoDomainEvent(queryClient, "session_changed");

    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.all,
    });
  });

  it("resetCarritoCaches elimina queries del dominio carritos", () => {
    const queryClient = createTestQueryClient();

    queryClient.setQueryData(carritoQueryKeys.activo(), { id: 1, items: [] });
    queryClient.setQueryData(carritoQueryKeys.lista(), { items: [], total: 0 });

    resetCarritoCaches(queryClient);

    expect(queryClient.getQueryData(carritoQueryKeys.activo())).toBeUndefined();
    expect(queryClient.getQueryData(carritoQueryKeys.lista())).toBeUndefined();
  });

  it("invalidateCarritoLista solo invalida la lista", async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await invalidateCarritoLista(queryClient);

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: carritoQueryKeys.lista(),
    });
    expect(invalidateSpy).toHaveBeenCalledTimes(1);
  });
});
