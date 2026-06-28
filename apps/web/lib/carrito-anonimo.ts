import type { ProductoResumen } from "@tfg/shared";

const CLAVE_CARRITO_ANONIMO = "carritoAnonimo";
export const EVENTO_CARRITO_ANONIMO_ACTUALIZADO = "carritoAnonimoActualizado";

export interface CarritoAnonimoItem {
  productoId: number;
  cantidad: number;
  producto?: ProductoResumen;
}

export interface CarritoAnonimoStorage {
  items: CarritoAnonimoItem[];
}

export class CarritoAnonimoStorageError extends Error {
  constructor(message = "El navegador no permite usar almacenamiento local para el carrito anónimo.") {
    super(message);
    this.name = "CarritoAnonimoStorageError";
  }
}

function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length(): number {
      return store.size;
    },
    key: (index: number): string | null => Array.from(store.keys())[index] ?? null,
    getItem: (key: string): string | null => store.get(key) ?? null,
    setItem: (key: string, value: string): void => {
      store.set(key, value);
    },
    removeItem: (key: string): void => {
      store.delete(key);
    },
    clear: (): void => {
      store.clear();
    },
  } as Storage;
}

let memoryStorage: Storage | null = null;

function getMemoryStorage(): Storage {
  if (!memoryStorage) {
    memoryStorage = createMemoryStorage();
  }
  return memoryStorage;
}

function asegurarLocalStorageDisponible(): Storage {
  if (typeof window === "undefined") {
    return getMemoryStorage();
  }

  try {
    return window.localStorage;
  } catch {
    throw new CarritoAnonimoStorageError();
  }
}

function normalizarItems(items: unknown): CarritoAnonimoItem[] {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .filter((item): item is CarritoAnonimoItem => {
      if (typeof item !== "object" || item === null) {
        return false;
      }

      const record = item as Record<string, unknown>;
      return (
        typeof record.productoId === "number" &&
        Number.isInteger(record.productoId) &&
        record.productoId > 0 &&
        typeof record.cantidad === "number" &&
        Number.isInteger(record.cantidad) &&
        record.cantidad >= 1 &&
        record.cantidad <= 99
      );
    })
    .map((item) => ({ productoId: item.productoId, cantidad: item.cantidad }));
}

function leerStorage(storage: Storage): CarritoAnonimoStorage {
  const raw = storage.getItem(CLAVE_CARRITO_ANONIMO);
  if (!raw) {
    return { items: [] };
  }

  try {
    const parsed = JSON.parse(raw) as { items?: unknown };
    return { items: normalizarItems(parsed.items) };
  } catch {
    return { items: [] };
  }
}

function guardarStorage(storage: Storage, carrito: CarritoAnonimoStorage): void {
  try {
    storage.setItem(CLAVE_CARRITO_ANONIMO, JSON.stringify(carrito));
  } catch {
    throw new CarritoAnonimoStorageError();
  }

  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(EVENTO_CARRITO_ANONIMO_ACTUALIZADO));
  }
}

function validarCantidad(cantidad: number): void {
  if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad > 99) {
    throw new Error("La cantidad debe estar entre 1 y 99.");
  }
}

export function getCarritoAnonimo(): CarritoAnonimoStorage {
  const storage = asegurarLocalStorageDisponible();
  return leerStorage(storage);
}

export function addItem(productoId: number, cantidad: number): CarritoAnonimoStorage {
  validarCantidad(cantidad);
  const storage = asegurarLocalStorageDisponible();
  const carrito = leerStorage(storage);
  const index = carrito.items.findIndex((item) => item.productoId === productoId);

  if (index === -1) {
    const actualizado = { items: [...carrito.items, { productoId, cantidad }] };
    guardarStorage(storage, actualizado);
    return actualizado;
  }

  const cantidadActualizada = carrito.items[index].cantidad + cantidad;
  if (cantidadActualizada > 99) {
    throw new Error("La cantidad máxima por producto es 99.");
  }

  const actualizado = {
    items: carrito.items.map((item) =>
      item.productoId === productoId ? { ...item, cantidad: cantidadActualizada } : item,
    ),
  };
  guardarStorage(storage, actualizado);
  return actualizado;
}

export function updateItem(productoId: number, cantidad: number): CarritoAnonimoStorage {
  validarCantidad(cantidad);
  const storage = asegurarLocalStorageDisponible();
  const carrito = leerStorage(storage);
  const actualizado = {
    items: carrito.items.map((item) =>
      item.productoId === productoId ? { ...item, cantidad } : item,
    ),
  };
  guardarStorage(storage, actualizado);
  return actualizado;
}

export function removeItem(productoId: number): CarritoAnonimoStorage {
  const storage = asegurarLocalStorageDisponible();
  const carrito = leerStorage(storage);
  const actualizado = {
    items: carrito.items.filter((item) => item.productoId !== productoId),
  };
  guardarStorage(storage, actualizado);
  return actualizado;
}

export function loadSnapshot(items: CarritoAnonimoItem[]): CarritoAnonimoStorage {
  const normalizados = normalizarItems(items);
  const storage = asegurarLocalStorageDisponible();
  const carrito: CarritoAnonimoStorage = { items: normalizados };
  guardarStorage(storage, carrito);
  return carrito;
}

export function setItemQuantity(productoId: number, cantidad: number): CarritoAnonimoStorage {
  validarCantidad(cantidad);
  const storage = asegurarLocalStorageDisponible();
  const carrito = leerStorage(storage);
  const index = carrito.items.findIndex((item) => item.productoId === productoId);

  if (index === -1) {
    return addItem(productoId, cantidad);
  }

  return updateItem(productoId, cantidad);
}

export function serializeForAuth(): CarritoAnonimoItem[] {
  return getCarritoAnonimo().items.map(({ productoId, cantidad }) => ({ productoId, cantidad }));
}

export function clearCarritoAnonimo(): void {
  const storage = asegurarLocalStorageDisponible();
  try {
    storage.removeItem(CLAVE_CARRITO_ANONIMO);
  } catch {
    throw new CarritoAnonimoStorageError();
  }

  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(EVENTO_CARRITO_ANONIMO_ACTUALIZADO));
  }
}

export function getCantidadTotalItems(): number {
  return getCarritoAnonimo().items.reduce((acumulado, item) => acumulado + item.cantidad, 0);
}

export const CARRITO_ANONIMO_STORAGE_KEY = CLAVE_CARRITO_ANONIMO;
