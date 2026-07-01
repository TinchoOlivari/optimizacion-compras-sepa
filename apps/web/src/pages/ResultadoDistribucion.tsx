import type React from "react";
import { useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import { ImagenProducto } from "@/components/ImagenProducto";
import { useDistribucion } from "@/features/carrito/hooks/useDistribucion";
import {
  iniciarCompraGuiada as iniciarCompraGuiadaApi,
  type AsignacionSucursalDistribucionResponse,
} from "@/lib/api";
import { formatearARS } from "@/lib/format";
import { useAppStore } from "@/store/appStore";
import { useToastStore } from "@/store/toastStore";

export default function ResultadoDistribucionPage(): React.ReactElement {
  const navigate = useNavigate();
  const setCompraGuiadaActiva = useAppStore((state) => state.setCompraGuiadaActiva);
  const addToast = useToastStore((state) => state.addToast);
  const distribucionQuery = useDistribucion();

  const carritoId = distribucionQuery.data?.carritoId;
  const resultado = distribucionQuery.data?.resultado;
  const iniciarMutation = useMutation({
    mutationFn: iniciarCompraGuiadaApi,
    onSuccess: (compra) => {
      setCompraGuiadaActiva(compra.id);
      navigate(`/compra-guiada/${compra.id}`);
    },
    onError: () => {
      addToast({
        message: "No se pudo iniciar la compra guiada. Intentá nuevamente.",
        variant: "error",
      });
    },
  });

  const totalProductos = useMemo(() => {
    if (!resultado) return 0;
    return resultado.asignaciones.reduce(
      (total, asignacion) =>
        total + asignacion.items.reduce((subtotal, item) => subtotal + item.cantidad, 0),
      0,
    );
  }, [resultado]);

  function iniciarCompraGuiada(): void {
    if (!carritoId || !resultado?.id) return;
    iniciarMutation.mutate(resultado.id);
  }

  const calculando = distribucionQuery.isPending || distribucionQuery.isFetching;

  if (calculando) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-6 pb-24">
        <VolverButton onClick={() => navigate(-1)} />
        <div className="h-7 w-60 animate-pulse rounded bg-muted" />
        <div className="mt-5 h-24 animate-pulse rounded-2xl bg-muted" />
        <div className="mt-4 space-y-3">
          <div className="h-44 animate-pulse rounded-2xl bg-muted" />
          <div className="h-44 animate-pulse rounded-2xl bg-muted" />
        </div>
      </main>
    );
  }

  if (distribucionQuery.isError || !resultado) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-6 pb-24">
        <VolverButton onClick={() => navigate(-1)} />
        <section className="rounded-2xl border border-error/20 bg-error-light p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-error">
            No se pudo calcular
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-text-primary">
            Resultado de distribución
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Revisá tu carrito o intentá nuevamente. La distribución depende de precios y sucursales
            disponibles.
          </p>
          <Button type="button" onClick={() => void distribucionQuery.refetch()} className="mt-5">
            Reintentar
          </Button>
        </section>
      </main>
    );
  }

  const ahorro = resultado.ahorro_estimado;

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 pb-24">
      <VolverButton onClick={() => navigate(-1)} />

      <header className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              Carrito optimizado
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-text-primary sm:text-3xl">
              Tu ruta de ahorro está lista
            </h1>
            <p className="pt-3 text-xs text-text-secondary">
              {resultado.asignaciones.length} sucursal
              {resultado.asignaciones.length === 1 ? "" : "es"} · {totalProductos} producto
              {totalProductos === 1 ? "" : "s"} asignado
              {totalProductos === 1 ? "" : "s"} ·{" "}
              {labelPreferencia(resultado.configuracion.preferencia)} · Radio{" "}
              {resultado.configuracion.radio_km} km
            </p>
          </div>

          <div className="grid min-w-[18rem] grid-cols-2 rounded-2xl border border-primary/15">
            <div className="rounded-l-2xl border-r border-primary/15 bg-primary-light p-4">
              <div className="flex items-center gap-1.5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary ">
                  Ahorro estimado
                </p>
                <AhorroInfoTooltip />
              </div>
              <p className="mt-1 text-2xl font-semibold text-primary">
                {ahorro != null ? formatearARS(ahorro) : "—"}
              </p>
            </div>
            <div className="rounded-r-2xl bg-surface p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-secondary">
                Subtotal
              </p>
              <p className="mt-1 text-2xl text-text-primary">
                {formatearARS(resultado.costo_total_estimado)}
              </p>
            </div>
          </div>
        </div>
      </header>

      {resultado.mensaje ? (
        <p className="mt-4 rounded-xl border border-accent/30 bg-accent-light px-3 py-2 text-sm text-text-primary">
          {resultado.mensaje}
        </p>
      ) : null}

      <section aria-label="Asignación por sucursal" className="mt-5 space-y-3">
        {resultado.asignaciones.map((asignacion) => (
          <SucursalCard key={asignacion.sucursal_id} asignacion={asignacion} />
        ))}
      </section>

      {resultado.items_no_asignados.length > 0 ? (
        <section
          aria-label="Productos no asignados"
          className="mt-4 rounded-2xl border border-error/20 bg-error-light p-4"
        >
          <h2 className="text-base font-semibold text-text-primary">Productos no encontrados</h2>
          <p className="mt-1 text-sm text-text-secondary">
            No están disponibles dentro del radio y las restricciones elegidas.
          </p>
          <ul className="mt-3 space-y-2">
            {resultado.items_no_asignados.map((item) => (
              <li
                key={item.item_carrito_id}
                className="flex items-center gap-3 rounded-xl bg-surface p-2"
              >
                <ProductoImagen src={item.url_imagen} nombre={item.nombre_producto} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">
                    {item.nombre_producto}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {iniciarMutation.isError ? (
        <p className="mt-4 rounded-xl border border-error/20 bg-error-light px-3 py-2 text-sm text-error">
          No se pudo iniciar la compra guiada. Intentá nuevamente.
        </p>
      ) : null}

      <div className="mt-6 flex justify-end">
        <Button
          type="button"
          onClick={iniciarCompraGuiada}
          disabled={!resultado.id || iniciarMutation.isPending}
          className="w-full sm:w-auto sm:px-8"
        >
          {iniciarMutation.isPending ? "Iniciando..." : "Comenzar recorrido"}
        </Button>
      </div>
    </main>
  );
}

function VolverButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-4 inline-flex min-h-[40px] items-center gap-2 rounded-full border border-border bg-surface px-3 text-sm font-medium text-secondary shadow-sm hover:bg-muted"
    >
      <span aria-hidden="true">←</span>
      Volver
    </button>
  );
}

function AhorroInfoTooltip(): React.ReactElement {
  return (
    <div className="group relative inline-flex z-10">
      <button
        type="button"
        aria-label="Cómo se calcula el ahorro estimado"
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-primary/30 text-[10px] font-semibold leading-none text-primary outline-none transition hover:bg-primary/10 focus-visible:ring-2 focus-visible:ring-primary/30"
      >
        i
      </button>
      <div className="pointer-events-none absolute left-0 top-full z-10 mt-2 hidden w-64 rounded-xl border border-border bg-surface p-3 text-left text-xs normal-case tracking-normal text-text-secondary shadow-lg group-hover:block group-focus-within:block">
        El ahorro compara el precio elegido para cada producto con el precio promedio de ese mismo producto entre las sucursales del radio configurado.
      </div>
    </div>
  );
}

function SucursalCard({ asignacion }: { asignacion: AsignacionSucursalDistribucionResponse }) {
  const cantidadItems = asignacion.items.reduce((total, item) => total + item.cantidad, 0);
  const direccion = formatearDireccion(asignacion);
  const mapsUrl = crearGoogleMapsUrl(asignacion);

  return (
    <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      <div className="grid gap-0 md:grid-cols-[15rem_1fr]">
        <div className="border-b border-border bg-muted/60 p-4 md:border-b-0 md:border-r">
          <div className="flex items-center gap-3">
            <SucursalLogo
              src={asignacion.bandera_logo_url}
              nombre={asignacion.bandera_nombre ?? asignacion.comercio}
            />
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-text-primary">
                {asignacion.sucursal}
              </h2>
              <p className="truncate text-xs text-secondary">
                {asignacion.bandera_nombre ?? asignacion.comercio}
              </p>
            </div>
          </div>
          {direccion ? (
            <p className="mt-3 text-xs leading-5 text-text-secondary">⌖ {direccion}</p>
          ) : null}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {asignacion.distancia_km != null ? (
              <span className="font-semibold text-primary">
                {asignacion.distancia_km.toFixed(1)} km
              </span>
            ) : null}
            <a
              href={mapsUrl}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-secondary hover:text-primary"
            >
              Abrir mapa ↗
            </a>
          </div>
        </div>

        <div className="p-3 sm:p-4">
          <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
            <p className="text-sm text-text-secondary">
              {cantidadItems} producto{cantidadItems === 1 ? "" : "s"}
            </p>
            <p className="text-base font-semibold text-text-primary">
              {formatearARS(asignacion.subtotal)}
            </p>
          </div>

          <ul className="mt-3 space-y-2">
            {asignacion.items.map((item) => (
              <li
                key={item.item_carrito_id}
                className="flex items-center gap-3 rounded-xl bg-background p-2"
              >
                <ProductoImagen src={item.url_imagen} nombre={item.nombre_producto} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">
                    {item.nombre_producto}
                  </p>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    {item.cantidad} × {formatearARS(item.precio_unitario)}
                  </p>
                </div>
                <p className="text-right text-sm font-semibold text-text-primary">
                  {formatearARS(item.subtotal)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  );
}

function SucursalLogo({ src, nombre }: { src: string | null; nombre: string }) {
  const url = normalizarAssetUrl(src);
  const iniciales = nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase())
    .join("");

  if (!url) {
    return (
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface text-sm font-semibold text-primary shadow-sm">
        {iniciales || "S"}
      </div>
    );
  }

  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface p-1.5 shadow-sm">
      <img
        src={url}
        alt={`Logo de ${nombre}`}
        className="max-h-full max-w-full object-contain"
        loading="lazy"
      />
    </div>
  );
}

function ProductoImagen({ src, nombre }: { src: string | null; nombre: string }) {
  if (!src) {
    return (
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-sm font-semibold text-text-secondary/60">
        {nombre[0]?.toUpperCase() ?? "P"}
      </div>
    );
  }

  return (
    <ImagenProducto
      src={src}
      alt={nombre}
      className="h-10 w-10 shrink-0 rounded-lg border border-border bg-surface"
    />
  );
}

function formatearDireccion(asignacion: AsignacionSucursalDistribucionResponse): string {
  return [asignacion.direccion, asignacion.localidad, asignacion.provincia]
    .filter(Boolean)
    .join(", ");
}

function crearGoogleMapsUrl(asignacion: AsignacionSucursalDistribucionResponse): string {
  if (Number.isFinite(asignacion.latitud) && Number.isFinite(asignacion.longitud)) {
    return `https://www.google.com/maps/search/?api=1&query=${asignacion.latitud},${asignacion.longitud}`;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(formatearDireccion(asignacion) || asignacion.sucursal)}`;
}

function normalizarAssetUrl(src: string | null): string | null {
  if (!src) return null;
  if (src.startsWith("http") || src.startsWith("/")) return src;
  return `/${src}`;
}

function labelPreferencia(preferencia: string): string {
  if (preferencia === "MENOR_PRECIO") return "Menor precio";
  if (preferencia === "MENOR_DESPLAZAMIENTO") return "Menor distancia";
  return "Balanceado";
}
