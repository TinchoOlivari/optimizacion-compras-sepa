import type React from "react";
import { useCallback, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { CantidadStepper } from "@/components/CantidadStepper";
import { ImagenProducto } from "@/components/ImagenProducto";
import { Modal } from "@/components/Modal";
import { useCarritoActivo } from "@/features/carrito/hooks/useCarritoActivo";
import { useCarritoMutations } from "@/features/carrito/hooks/useCarritoMutations";
import { useProductoDetalle } from "@/features/catalogo/hooks/useProductoDetalle";
import { usePreferencias } from "@/features/preferencias/hooks/usePreferencias";
import { filtrosGeoParaDetalleProducto } from "@/features/preferencias/lib/filtrosGeo";
import { formatearARS } from "@/lib/format";
import { useAuthStore } from "@/store/authStore";

export default function ProductoDetallePage(): React.ReactElement {
  const navigate = useNavigate();
  const { id } = useParams();
  const productoId = Number(id);
  const usuario = useAuthStore((state) => state.usuario);
  const autenticado = !!usuario;
  const [cantidad, setCantidad] = useState(1);
  const [tokenExpirado, setTokenExpirado] = useState(false);
  const [imagenResuelta, setImagenResuelta] = useState(false);

  const carritoQuery = useCarritoActivo(autenticado);

  const { addItemMutation } = useCarritoMutations({
    autenticado,
    carritoActivo: carritoQuery.data,
    onTokenExpirado: () => setTokenExpirado(true),
  });

  const preferenciasQuery = usePreferencias(autenticado);

  const filtrosGeo = useMemo(
    () => filtrosGeoParaDetalleProducto(preferenciasQuery.data),
    [preferenciasQuery.data],
  );

  const productoQuery = useProductoDetalle(productoId, filtrosGeo);

  function agregarAlCarrito(): void {
    if (!productoQuery.data) return;
    addItemMutation.mutate({ productoId: productoQuery.data.producto.id, cantidad });
  }

  const onImagenResuelta = useCallback(() => setImagenResuelta(true), []);

  if (!Number.isFinite(productoId) || productoId <= 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <p className="text-text-secondary">Producto no encontrado.</p>
        <Button type="button" variant="ghost" onClick={() => navigate(-1)} className="mt-4 px-0 text-primary">
          ← Volver
        </Button>
      </main>
    );
  }

  if (productoQuery.isLoading && !productoQuery.data) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="h-8 w-24 animate-pulse rounded bg-muted" />
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_1fr]">
          <div className="h-96 animate-pulse rounded-xl bg-muted" />
          <div className="h-96 animate-pulse rounded-xl bg-muted" />
        </div>
      </main>
    );
  }

  if (productoQuery.isError || !productoQuery.data) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <p className="text-error">No pudimos cargar el producto.</p>
        <Button type="button" variant="secondary" onClick={() => void productoQuery.refetch()} className="mt-4">
          Reintentar
        </Button>
        <Button type="button" variant="ghost" onClick={() => navigate(-1)} className="mt-4 px-0 text-primary">
          ← Volver
        </Button>
      </main>
    );
  }

  const { producto, precios, filtro_radio_activo, mensaje } = productoQuery.data;
  const precioMinimo = precios.find((precio) => precio.precio_minimo);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Button type="button" variant="ghost" onClick={() => navigate(-1)} className="mb-6 px-0 text-primary">
        ← Volver
      </Button>

      <div className="grid gap-8 lg:grid-cols-[1fr_1fr]">
        <section className="rounded-xl border border-border bg-surface p-6 shadow-sm">
          <div className="flex justify-center">
            {producto.url_imagen ? (
              <ImagenProducto
                src={producto.url_imagen}
                alt=""
                className="h-72 w-72 rounded-lg object-contain"
                onResuelta={onImagenResuelta}
              />
            ) : (
              <div className="flex h-72 w-72 items-center justify-center rounded-lg bg-muted">
                <span className="text-sm text-text-secondary">Sin imagen</span>
              </div>
            )}
          </div>

          <div
            className={`transition-opacity duration-300 ${producto.url_imagen && !imagenResuelta ? "invisible opacity-0" : "opacity-100"}`}
          >
            <h1 className="mt-6 text-3xl font-bold text-text-primary">{producto.nombre}</h1>
            <p className="mt-2 text-xl text-text-secondary">
              {producto.marca ?? "Sin marca"} · {producto.presentacion ?? "Sin presentación"}
            </p>
            <p className="mt-4 text-sm text-text-secondary">EAN: {producto.codigo_ean}</p>
          </div>

          <div
            className={`transition-opacity duration-300 ${producto.url_imagen && !imagenResuelta ? "invisible opacity-0" : "opacity-100"}`}
          >
            <div className="mt-6 flex items-center justify-between rounded-xl border border-border bg-background p-3">
              <span className="font-semibold text-text-primary">Cantidad en carrito</span>
              <CantidadStepper
                cantidad={cantidad}
                onDecrement={() => setCantidad((actual) => Math.max(1, actual - 1))}
                onIncrement={() => setCantidad((actual) => Math.min(99, actual + 1))}
                labelMenos="Disminuir cantidad"
                labelMas="Aumentar cantidad"
              />
            </div>

            <Button
              type="button"
              onClick={agregarAlCarrito}
              disabled={addItemMutation.isPending}
              className="mt-4 w-full"
            >
              {addItemMutation.isPending ? "Agregando..." : "Agregar al carrito"}
            </Button>
          </div>
        </section>

        <section aria-labelledby="precios-disponibles" className="pt-2">
          <h2 id="precios-disponibles" className="text-2xl font-bold text-secondary">
            Precios disponibles
          </h2>
          <p className="mt-4 text-sm text-text-secondary">
            {filtro_radio_activo && filtrosGeo
              ? `Hasta 6 supermercados más cercanos en tu radio de ${filtrosGeo.radio_km} km.`
              : "Indicá tu ubicación para ver precios cercanos."}
          </p>
          {mensaje ? <p className="mt-2 text-sm text-text-secondary">{mensaje}</p> : null}

          {precios.length === 0 ? (
            <p className="mt-5 text-sm text-text-secondary">No hay precios disponibles para este producto.</p>
          ) : (
            <ul className="mt-5 space-y-3">
              {precios.map((precio) => (
                <li
                  key={precio.comercio_id}
                  className={`rounded-xl border bg-surface p-4 shadow-sm ${
                    precio.precio_minimo ? "border-success" : "border-border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-bold text-text-primary">{precio.comercio}</h3>
                      <p className="mt-2 text-sm text-text-secondary">
                        {precio.distancia_km != null ? `⊙ ${precio.distancia_km.toFixed(1)} km · ` : ""}
                        {precio.direccion ?? precio.sucursal}
                      </p>
                      {precioMinimo?.comercio_id === precio.comercio_id ? (
                        <span className="mt-2 inline-flex rounded-full bg-success-light px-2 py-1 text-xs font-semibold text-success">
                          Más barato
                        </span>
                      ) : null}
                    </div>
                    <p className="text-lg font-bold text-text-primary">{formatearARS(precio.precio)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

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
