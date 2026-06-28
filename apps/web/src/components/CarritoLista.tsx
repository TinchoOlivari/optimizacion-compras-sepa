import type { ProductoResumen } from "@tfg/shared";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { CantidadStepper } from "@/components/CantidadStepper";
import { ImagenProducto } from "@/components/ImagenProducto";

export interface CarritoListaItem {
  itemId?: number;
  productoId: number;
  cantidad: number;
  producto?: ProductoResumen | null;
}

interface CarritoListaProps {
  items: CarritoListaItem[];
  onChangeCantidad: (productoId: number, itemId: number | undefined, cantidad: number) => void;
  onEliminar: (productoId: number, itemId?: number) => void;
}

function ItemCarrito({
  item,
  onChangeCantidad,
  onEliminar,
}: {
  item: CarritoListaItem;
  onChangeCantidad: CarritoListaProps["onChangeCantidad"];
  onEliminar: CarritoListaProps["onEliminar"];
}) {
  const { itemId, productoId, cantidad, producto } = item;
  const tieneImagen = !!producto?.url_imagen;
  const [imagenResuelta, setImagenResuelta] = useState(!tieneImagen);
  const nombreProducto = producto?.nombre ?? "Producto";

  const onImagenResuelta = useCallback(() => setImagenResuelta(true), []);

  return (
    <li className="rounded-xl border border-border bg-surface p-4 shadow-sm">
      <div className="flex items-start gap-4">
        <Link
          to={`/productos/${productoId}`}
          className="flex min-w-0 flex-1 items-start gap-4 rounded-lg outline-none"
          aria-label={`Ver detalle de ${nombreProducto}`}
        >
          <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted">
            {tieneImagen ? (
              <ImagenProducto
                src={producto!.url_imagen!}
                alt=""
                className="h-full w-full"
                onResuelta={onImagenResuelta}
              />
            ) : null}
          </div>
          <div
            className={`min-w-0 flex-1 transition-opacity duration-300 ${imagenResuelta ? "opacity-100" : "invisible opacity-0"}`}
          >
            <p className="text-base font-semibold text-text-primary hover:text-primary">
              {nombreProducto}
            </p>
            <p className="text-sm text-text-secondary">
              {producto?.marca ?? "Sin marca"} · {producto?.presentacion ?? "Sin presentación"}
            </p>
            <p className="text-xs text-text-secondary">EAN: {producto?.codigo_ean ?? "—"}</p>
          </div>
        </Link>
        <div
          className={`flex flex-shrink-0 items-center gap-2 transition-opacity duration-300 ${imagenResuelta ? "opacity-100" : "invisible opacity-0"}`}
        >
          <CantidadStepper
            cantidad={cantidad}
            onDecrement={() =>
              cantidad === 1
                ? onEliminar(productoId, itemId)
                : onChangeCantidad(productoId, itemId, cantidad - 1)
            }
            onIncrement={() => onChangeCantidad(productoId, itemId, cantidad + 1)}
            labelMenos={`Disminuir cantidad de ${nombreProducto}`}
            labelMas={`Aumentar cantidad de ${nombreProducto}`}
          />
          <button
            type="button"
            onClick={() => onEliminar(productoId, itemId)}
            aria-label={`Eliminar ${nombreProducto} del carrito`}
            className="ml-1 flex h-8 w-8 items-center justify-center rounded-lg border border-error text-error hover:bg-error-light"
          >
            ×
          </button>
        </div>
      </div>
    </li>
  );
}

export function CarritoLista({ items, onChangeCantidad, onEliminar }: CarritoListaProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <ul className="grid gap-3" aria-label="Productos en el carrito">
      {items.map((item) => (
        <ItemCarrito
          key={item.productoId}
          item={item}
          onChangeCantidad={onChangeCantidad}
          onEliminar={onEliminar}
        />
      ))}
    </ul>
  );
}