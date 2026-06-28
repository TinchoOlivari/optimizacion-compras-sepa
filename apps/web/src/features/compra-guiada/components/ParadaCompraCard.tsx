import type React from "react";
import { EstadoItem } from "@tfg/shared";

import { formatearARS } from "@/lib/format";

import { ItemCompraCard } from "./ItemCompraCard";
import type { ParadaCompraViewModel } from "../lib/buildCompraGuiada";
import { formatearDireccionParada } from "../lib/buildCompraGuiada";

interface ParadaCompraCardProps {
  parada: ParadaCompraViewModel;
  onEstadoChange: (progresoItemId: number, estado: EstadoItem) => void;
}

export function ParadaCompraCard({
  parada,
  onEstadoChange,
}: ParadaCompraCardProps): React.ReactElement {
  const direccion = formatearDireccionParada(parada);
  const logoNombre = parada.banderaNombre ?? parada.comercio;

  return (
    <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      <header className="border-b border-border bg-muted/40 px-3 py-2.5">
        <div className="flex items-start gap-2.5">
          <SucursalLogo src={parada.banderaLogoUrl} nombre={logoNombre} />
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">
                  Parada {parada.numero}
                </p>
                <h2 className="truncate text-sm font-semibold text-text-primary">
                  {parada.sucursal}
                </h2>
                {direccion ? (
                  <p className="truncate text-[11px] text-text-secondary/70">{direccion}</p>
                ) : null}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <p className="text-sm font-semibold text-text-primary">
                  {formatearARS(parada.subtotal)}
                </p>
                {parada.distanciaKm != null ? (
                  <p className="text-[11px] font-medium text-primary">
                    {parada.distanciaKm.toFixed(1)} km
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </header>

      <ul className="space-y-1.5 p-2">
        {parada.items.map((item) => (
          <ItemCompraCard key={item.itemCarritoId} item={item} onEstadoChange={onEstadoChange} />
        ))}
      </ul>
    </article>
  );
}

function SucursalLogo({ src, nombre }: { src: string | null; nombre: string }): React.ReactElement {
  const url = normalizarAssetUrl(src);
  const iniciales = nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase())
    .join("");

  if (!url) {
    return (
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-[11px] font-semibold text-primary shadow-sm">
        {iniciales || "S"}
      </div>
    );
  }

  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface p-1 shadow-sm">
      <img
        src={url}
        alt={`Logo de ${nombre}`}
        className="max-h-full max-w-full object-contain"
        loading="lazy"
      />
    </div>
  );
}

function normalizarAssetUrl(src: string | null): string | null {
  if (!src) return null;
  if (src.startsWith("http") || src.startsWith("/")) return src;
  return `/${src}`;
}
