"use client";

import type React from "react";
import { useCallback, useMemo, useState } from "react";

import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import { CarritoLista } from "@/components/CarritoLista";
import { ImagenProducto } from "@/components/ImagenProducto";
import { Modal } from "@/components/Modal";
import { useCarritoActivo } from "@/features/carrito/hooks/useCarritoActivo";
import { useCarritoAnonimo } from "@/features/carrito/hooks/useCarritoAnonimo";
import { useCarritoMutations } from "@/features/carrito/hooks/useCarritoMutations";
import { useBuscarProductos } from "@/features/catalogo/hooks/useBuscarProductos";
import {
  busquedaHabilitada,
  esEan13,
  MIN_CARACTERES_BUSQUEDA_NOMBRE,
} from "@/features/catalogo/lib/busqueda";
import { useAuthStore } from "@/store/authStore";
import type { ProductoResumen } from "@tfg/shared";

interface SugerenciaItemProps {
  producto: ProductoResumen;
  onAgregar: (productoId: number, cantidad: number) => void;
  onCerrarAutocompletar: () => void;
}

function SugerenciaItem({ producto, onAgregar, onCerrarAutocompletar }: SugerenciaItemProps) {
  const tieneImagen = !!producto.url_imagen;
  const [imagenResuelta, setImagenResuelta] = useState(!tieneImagen);

  const onImagenResuelta = useCallback(() => setImagenResuelta(true), []);

  return (
    <li
      role="option"
      aria-selected="false"
      className="flex items-center gap-3 rounded-lg p-2 hover:bg-muted"
    >
      <Link
        to={`/productos/${producto.id}`}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg outline-none"
        onClick={onCerrarAutocompletar}
      >
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted">
          {tieneImagen ? (
            <ImagenProducto
              src={producto.url_imagen!}
              alt=""
              className="h-full w-full"
              onResuelta={onImagenResuelta}
            />
          ) : (
            <span className="text-xs text-text-secondary">Sin imagen</span>
          )}
        </div>
        <div
          className={`min-w-0 flex-1 transition-opacity duration-300 ${imagenResuelta ? "opacity-100" : "invisible opacity-0"}`}
        >
          <p className="truncate text-sm font-medium text-text-primary">
            {producto.nombre}
          </p>
          <p className="truncate text-xs text-text-secondary">
            {producto.marca ?? "Sin marca"} · {producto.presentacion ?? "Sin presentación"}
          </p>
          <p className="text-xs text-text-secondary">EAN: {producto.codigo_ean}</p>
        </div>
      </Link>
      <Button
        type="button"
        variant="secondary"
        className={`flex-shrink-0 transition-opacity duration-300 ${imagenResuelta ? "opacity-100" : "invisible opacity-0"}`}
        onClick={() => onAgregar(producto.id, 1)}
        aria-label={`Agregar ${producto.nombre} al carrito`}
      >
        Agregar
      </Button>
    </li>
  );
}

export default function HomePage(): React.ReactElement {
  const navigate = useNavigate();
  const usuario = useAuthStore((state) => state.usuario);
  const autenticado = !!usuario;
  const [inputBusqueda, setInputBusqueda] = useState("");
  const busquedaDebounced = useDebouncedValue(inputBusqueda);
  const [mostrarAutocompletar, setMostrarAutocompletar] = useState(false);
  const [confirmarVaciarCarrito, setConfirmarVaciarCarrito] = useState(false);
  const [tokenExpirado, setTokenExpirado] = useState(false);

  const carritoAnonimo = useCarritoAnonimo();
  const carritoPersistidoQuery = useCarritoActivo(autenticado);

  const carritoActivo = useMemo(() => {
    return carritoPersistidoQuery.data ?? undefined;
  }, [carritoPersistidoQuery.data]);

  const {
    addItemMutation,
    updateItemMutation,
    removeItemMutation,
    vaciarCarritoMutation,
  } = useCarritoMutations({
    autenticado,
    carritoActivo,
    onAnonimoChange: carritoAnonimo.refresh,
    onTokenExpirado: () => setTokenExpirado(true),
  });

  const busquedaQuery = useBuscarProductos(busquedaDebounced);

  const inputBusquedaTrim = inputBusqueda.trim();
  const busquedaDebouncedTrim = busquedaDebounced.trim();
  const busquedaPendiente =
    busquedaHabilitada(inputBusquedaTrim) && inputBusquedaTrim !== busquedaDebouncedTrim;
  const busquedaSincronizada = inputBusquedaTrim === busquedaDebouncedTrim;

  function cambiarCantidadItem(productoId: number, itemId: number | undefined, proximaCantidad: number): void {
    if (proximaCantidad < 1 || proximaCantidad > 99) {
      return;
    }

    updateItemMutation.mutate({ productoId, cantidad: proximaCantidad, itemId });
  }

  function eliminarProducto(productoId: number, itemId?: number): void {
    removeItemMutation.mutate({ productoId, itemId });
  }

  function agregarProducto(productoId: number, cantidad: number): void {
    addItemMutation.mutate({ productoId, cantidad });
  }

  const itemsRender = useMemo(() => {
    if (autenticado) {
      return (carritoPersistidoQuery.data?.items ?? []).map((item) => ({
        itemId: item.id,
        productoId: item.producto_id,
        cantidad: item.cantidad,
        producto: item.producto ?? null,
      }));
    }

    return carritoAnonimo.items.map((item) => ({
      itemId: undefined as number | undefined,
      productoId: item.productoId,
      cantidad: item.cantidad,
      producto: item.producto ?? null,
    }));
  }, [autenticado, carritoPersistidoQuery.data, carritoAnonimo.items]);

  const carritoVacio = itemsRender.length === 0;
  const sinCarritoActivo =
    autenticado &&
    !carritoPersistidoQuery.isLoading &&
    !carritoPersistidoQuery.isError &&
    carritoPersistidoQuery.data === null;
  const buscando =
    busquedaPendiente || busquedaQuery.isFetching || busquedaQuery.isLoading;
  const errorBusqueda = busquedaQuery.error;
  const sugerencias = busquedaQuery.data;
  const totalProductos = autenticado
    ? carritoPersistidoQuery.data?.items.length ?? 0
    : carritoAnonimo.totalItems;
  const tituloCarrito = sinCarritoActivo
    ? "Carrito"
    : carritoActivo?.titulo?.trim()
      ? carritoActivo.titulo
      : "Carrito sin título";

  return (
    <main className="mx-auto max-w-4xl px-4 py-12 pb-32">
      <section>
        <div className="flex flex-wrap items-center gap-4">
          <h1 className="text-4xl font-bold text-text-primary">{tituloCarrito}</h1>
          {carritoActivo ? (
            <span className="inline-flex items-center rounded-full border border-primary bg-primary-light px-3 py-1 text-sm font-semibold text-primary">
              Carrito activo
            </span>
          ) : null}
        </div>
        <p className="mt-4 text-lg text-text-secondary">
          {totalProductos} producto{totalProductos === 1 ? "" : "s"}
        </p>

        <div className="relative mt-8">
          <label htmlFor="buscar-productos" className="sr-only">
            Buscar producto
          </label>
          <div className="relative">
            <span aria-hidden="true" className="absolute left-5 top-1/2 -translate-y-1/2 text-4xl text-text-secondary/70">
              ⌕
            </span>
            <input
              id="buscar-productos"
              value={inputBusqueda}
              onChange={(event) => {
                setInputBusqueda(event.target.value);
                setMostrarAutocompletar(true);
              }}
              onFocus={() => setMostrarAutocompletar(true)}
              onBlur={() => window.setTimeout(() => setMostrarAutocompletar(false), 200)}
              placeholder="Buscar por nombre o código EAN..."
              autoComplete="off"
              aria-autocomplete="list"
              aria-controls="sugerencias-busqueda"
              className="w-full rounded-xl border border-slate-300 bg-white px-14 py-4 text-lg shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            {inputBusqueda ? (
              <button
                type="button"
                onClick={() => {
                  setInputBusqueda("");
                  setMostrarAutocompletar(false);
                }}
                aria-label="Limpiar búsqueda"
                className="absolute right-5 top-1/2 -translate-y-1/2 text-2xl text-text-secondary hover:text-text-primary"
              >
                ×
              </button>
            ) : null}
          </div>

          {mostrarAutocompletar && busquedaHabilitada(inputBusquedaTrim) ? (
            <div
              id="sugerencias-busqueda"
              role="listbox"
              className="absolute z-20 mt-2 w-full rounded-xl border border-border bg-surface p-2 shadow-card"
            >
              {buscando ? (
                <div className="space-y-2 p-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="h-10 w-10 animate-pulse rounded-lg bg-muted" />
                      <div className="flex-1 space-y-1.5">
                        <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                        <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {!buscando && errorBusqueda ? (
                <div className="p-3 text-center">
                  <p className="text-sm text-error">No pudimos consultar el catálogo.</p>
                  <Button
                    variant="secondary"
                    onClick={() => void busquedaQuery.refetch()}
                    className="mt-2"
                  >
                    Reintentar
                  </Button>
                </div>
              ) : null}

              {!buscando && busquedaSincronizada && !errorBusqueda && sugerencias?.items.length === 0 ? (
                <p className="p-3 text-sm text-text-secondary">
                  No se encontraron productos para la búsqueda ingresada.
                </p>
              ) : null}

              {!buscando && busquedaSincronizada && !errorBusqueda && (sugerencias?.items.length ?? 0) > 0 ? (
                <ul role="listbox" className="max-h-80 overflow-auto">
                  {sugerencias?.items.map((producto) => (
                    <SugerenciaItem
                      key={producto.id}
                      producto={producto}
                      onAgregar={agregarProducto}
                      onCerrarAutocompletar={() => setMostrarAutocompletar(false)}
                    />
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </div>

        {inputBusquedaTrim && !esEan13(inputBusquedaTrim) && inputBusquedaTrim.length < MIN_CARACTERES_BUSQUEDA_NOMBRE ? (
          <p className="mt-2 text-sm text-text-secondary">
            Ingresá al menos {MIN_CARACTERES_BUSQUEDA_NOMBRE} caracteres o un EAN de 13 dígitos.
          </p>
        ) : null}
      </section>

      {autenticado && carritoPersistidoQuery.isLoading && carritoVacio ? (
        <section className="mt-10 space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-28 w-full animate-pulse rounded-xl bg-muted" />
          ))}
        </section>
      ) : null}

      {autenticado && carritoPersistidoQuery.isError ? (
        <section className="mt-10 rounded-xl border border-border bg-error-light p-4">
          <p className="text-sm text-error">No pudimos cargar tu carrito.</p>
          <Button
            variant="secondary"
            onClick={() => void carritoPersistidoQuery.refetch()}
            className="mt-2"
          >
            Reintentar
          </Button>
        </section>
      ) : null}

      {!carritoPersistidoQuery.isLoading && !carritoPersistidoQuery.isError && carritoVacio ? (
        <section className="mt-10 rounded-xl border border-border bg-surface p-8 text-center">
          {sinCarritoActivo ? (
            <>
              <p className="text-base font-medium text-text-primary">No tenés un carrito activo.</p>
              <p className="mt-1 text-sm text-text-secondary">
                Agregá un producto para crear uno automáticamente o{" "}
                <Link to="/carritos" className="font-medium text-primary hover:underline">
                  elegí uno en Mis carritos
                </Link>
                .
              </p>
            </>
          ) : (
            <>
              <p className="text-base font-medium text-text-primary">Tu carrito está vacío.</p>
              <p className="mt-1 text-sm text-text-secondary">Usá la barra de búsqueda para agregar productos.</p>
            </>
          )}
        </section>
      ) : null}

      {!carritoVacio ? (
        <section className="mt-10 space-y-5">
          <h2 className="sr-only">Productos en el carrito</h2>

          <CarritoLista
            items={itemsRender}
            onChangeCantidad={cambiarCantidadItem}
            onEliminar={eliminarProducto}
          />
        </section>
      ) : null}

      <footer className="fixed bottom-0 left-0 right-0 z-30 border-t border-border bg-surface p-4 shadow-[0_-2px_8px_rgba(0,0,0,0.06)]">
        <div className="mx-auto flex max-w-4xl items-center gap-3">
          {!carritoVacio ? (
            <Button
              type="button"
              variant="ghost"
              className="min-h-0 shrink-0 px-1 py-1 text-xs font-normal text-text-secondary hover:text-error"
              onClick={() => setConfirmarVaciarCarrito(true)}
            >
              Vaciar carrito
            </Button>
          ) : null}
          <Button
            type="button"
            disabled={carritoVacio || sinCarritoActivo}
            className="flex-1 text-base"
            onClick={() => {
              if (carritoVacio) return;
              if (!autenticado) {
                navigate("/login");
                return;
              }
              navigate("/distribuir");
            }}
          >
            Distribuir carrito ›
          </Button>
        </div>
      </footer>

      <Modal
        open={confirmarVaciarCarrito}
        title="Vaciar carrito"
        description="¿Querés quitar todos los productos del carrito? El carrito se mantiene guardado."
        onClose={() => setConfirmarVaciarCarrito(false)}
        secondaryAction={{ label: "Cancelar", onClick: () => setConfirmarVaciarCarrito(false) }}
        primaryAction={{
          label: vaciarCarritoMutation.isPending ? "Vaciando..." : "Vaciar",
          onClick: () => {
            vaciarCarritoMutation.mutate(undefined, {
              onSuccess: () => setConfirmarVaciarCarrito(false),
            });
          },
          variant: "destructive",
        }}
      />

      <Modal
        open={tokenExpirado}
        title="Sesión vencida"
        description="Tu sesión expiró. Iniciá sesión nuevamente para continuar."
        onClose={() => setTokenExpirado(false)}
        primaryAction={{
          label: "Iniciar sesión",
          onClick: () => {
            setTokenExpirado(false);
            navigate("/login");
          },
        }}
        secondaryAction={{ label: "Cancelar", onClick: () => setTokenExpirado(false) }}
      />
    </main>
  );
}
