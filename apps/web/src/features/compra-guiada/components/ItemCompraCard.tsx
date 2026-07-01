import type React from "react";
import { EstadoItem } from "@tfg/shared";

import { ImagenProducto } from "@/components/ImagenProducto";
import { formatearARS } from "@/lib/format";

import type { ItemCompraViewModel } from "../lib/buildCompraGuiada";

interface ItemCompraCardProps {
  item: ItemCompraViewModel;
  onEstadoChange: (progresoItemId: number, estado: EstadoItem) => void;
  actualizando: boolean;
}

export function ItemCompraCard({
  item,
  onEstadoChange,
  actualizando,
}: ItemCompraCardProps): React.ReactElement {
  const resuelto = item.estado !== EstadoItem.PENDIENTE;
  const esConseguido = item.estado === EstadoItem.CONSEGUIDO;
  const esNoEncontrado = item.estado === EstadoItem.NO_ENCONTRADO;
  const esDescartado = item.estado === EstadoItem.DESCARTADO;

  function toggleConseguido(): void {
    if (esConseguido) {
      onEstadoChange(item.progresoItemId, EstadoItem.PENDIENTE);
    } else {
      onEstadoChange(item.progresoItemId, EstadoItem.CONSEGUIDO);
    }
  }

  return (
    <li
      className={`rounded-xl border border-border bg-background p-2 transition ${
        esConseguido ? "opacity-50" : ""
      } ${esNoEncontrado ? "bg-error-light/40" : ""} ${esDescartado ? "opacity-40" : ""}`}
    >
      <div className="flex items-start gap-2">
        <button
          type="button"
          aria-label={
            esConseguido ? `Desmarcar ${item.nombre}` : `Marcar ${item.nombre} como conseguido`
          }
          onClick={toggleConseguido}
          disabled={actualizando}
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border-2 text-sm font-bold transition ${
            esConseguido
              ? "border-success bg-success text-white"
              : "border-border bg-surface text-transparent hover:border-success"
          }`}
        >
          {esConseguido ? "✓" : ""}
        </button>

        <div className="min-w-0 flex-1">
          <p
            className={`text-sm font-medium text-text-primary ${
              esConseguido || esDescartado ? "line-through" : ""
            }`}
          >
            {item.nombre}
          </p>
          <p className="mt-0.5 text-xs text-text-secondary">
            {actualizando ? "Buscando alternativa..." : `${item.cantidad} un. · ${formatearARS(item.subtotal)}`}
          </p>
        </div>

        <ProductoImagen src={item.urlImagen} nombre={item.nombre} />

        <div className="flex items-center gap-1">
          {resuelto ? (
            <button
              type="button"
              aria-label={`Deshacer estado de ${item.nombre}`}
              onClick={() => onEstadoChange(item.progresoItemId, EstadoItem.PENDIENTE)}
              disabled={actualizando}
              className="flex h-7 w-7 items-center justify-center rounded-full text-xs text-text-secondary hover:bg-muted"
            >
              ↺
            </button>
          ) : (
            <>
              <EstadoIconButton
                label={`Marcar ${item.nombre} como no encontrado`}
                symbol="×"
                className="bg-error-light/60 text-error hover:bg-error-light"
                disabled={actualizando}
                onClick={() => onEstadoChange(item.progresoItemId, EstadoItem.NO_ENCONTRADO)}
              />
              <EstadoIconButton
                label={`Descartar ${item.nombre}`}
                symbol="⊘"
                className="bg-muted text-text-secondary hover:bg-border"
                disabled={actualizando}
                onClick={() => onEstadoChange(item.progresoItemId, EstadoItem.DESCARTADO)}
              />
            </>
          )}
        </div>
      </div>
    </li>
  );
}

interface EstadoIconButtonProps {
  label: string;
  symbol: string;
  className: string;
  disabled: boolean;
  onClick: () => void;
}

function EstadoIconButton({
  label,
  symbol,
  className,
  disabled,
  onClick,
}: EstadoIconButtonProps): React.ReactElement {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold transition shadow-sm disabled:opacity-50 ${className}`}
    >
      <span aria-hidden="true">{symbol}</span>
    </button>
  );
}

function ProductoImagen({
  src,
  nombre,
}: {
  src: string | null;
  nombre: string;
}): React.ReactElement {
  if (!src) {
    return (
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-semibold text-text-secondary/60">
        {nombre[0]?.toUpperCase() ?? "P"}
      </div>
    );
  }

  return (
    <ImagenProducto
      src={src}
      alt={nombre}
      className="h-9 w-9 shrink-0 rounded-lg border border-border bg-surface"
    />
  );
}
