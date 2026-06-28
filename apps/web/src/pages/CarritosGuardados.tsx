import type React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import { Modal } from "@/components/Modal";
import { useCarritosLista } from "@/features/carrito/hooks/useCarritosLista";
import { useCarritosListaMutations } from "@/features/carrito/hooks/useCarritosListaMutations";
import { formatearFechaCarrito } from "@/lib/format";
import { useToastStore } from "@/store/toastStore";

export default function CarritosGuardadosPage(): React.ReactElement {
  const navigate = useNavigate();
  const addToast = useToastStore((state) => state.addToast);
  const [carritoAEliminar, setCarritoAEliminar] = useState<number | null>(null);

  const carritosQuery = useCarritosLista();
  const {
    crearMutation,
    activarMutation,
    renombrarMutation,
    eliminarMutation,
  } = useCarritosListaMutations({
    onCarritoActivado: () => navigate("/"),
    onCarritoEliminado: () => setCarritoAEliminar(null),
  });

  function editarTitulo(carritoId: number, tituloActual: string | null): void {
    const nuevoTitulo = window.prompt("Nuevo título del carrito", tituloActual ?? "");
    if (nuevoTitulo === null) return;
    const titulo = nuevoTitulo.trim();
    if (!titulo) {
      addToast({ message: "El título no puede estar vacío.", variant: "error" });
      return;
    }
    renombrarMutation.mutate({ carritoId, titulo });
  }

  const carritos = carritosQuery.data?.items ?? [];
  const carritoEliminar = carritos.find((c) => c.id === carritoAEliminar);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between gap-4">
        <h1 className="text-3xl font-bold text-text-primary">Mis carritos</h1>
        <Button
          type="button"
          disabled={crearMutation.isPending}
          onClick={() => crearMutation.mutate()}
        >
          {crearMutation.isPending ? "Creando..." : "Crear carrito nuevo"}
        </Button>
      </div>

      {carritosQuery.isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : null}

      {carritosQuery.isError ? (
        <div className="rounded-xl border border-border bg-error-light p-4">
          <p className="text-sm text-error">No pudimos cargar tus carritos.</p>
          <Button
            variant="secondary"
            onClick={() => void carritosQuery.refetch()}
            className="mt-2"
          >
            Reintentar
          </Button>
        </div>
      ) : null}

      {!carritosQuery.isLoading && !carritosQuery.isError && carritos.length === 0 ? (
        <p className="text-text-secondary">No tenés carritos guardados.</p>
      ) : null}

      <ul className="space-y-4" aria-label="Mis carritos guardados">
        {carritos.map((carrito) => (
          <li
            key={carrito.id}
            className={`rounded-xl border bg-surface p-5 shadow-sm ${
              carrito.activo ? "border-primary" : "border-border"
            }`}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-xl font-bold text-text-primary">{carrito.titulo ?? "Carrito sin título"}</h2>
                  {carrito.activo ? (
                    <span className="rounded-full border border-success bg-success-light px-2 py-0.5 text-xs font-semibold text-success">
                      Activo
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-sm text-text-secondary">
                  {carrito.cantidad_items} productos · Editado:{" "}
                  {formatearFechaCarrito(carrito.fecha_ultima_edicion)}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {!carrito.activo ? (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={activarMutation.isPending}
                    onClick={() => activarMutation.mutate(carrito.id)}
                  >
                    Seleccionar
                  </Button>
                ) : null}
                <Button
                  type="button"
                  variant="secondary"
                  ariaLabel={`Editar ${carrito.titulo ?? "carrito"}`}
                  disabled={renombrarMutation.isPending}
                  onClick={() => editarTitulo(carrito.id, carrito.titulo)}
                >
                  ✎
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  ariaLabel={`Eliminar ${carrito.titulo ?? "carrito"}`}
                  onClick={() => setCarritoAEliminar(carrito.id)}
                >
                  🗑
                </Button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <Modal
        open={carritoAEliminar !== null}
        title="Eliminar carrito"
        description={`¿Estás seguro de que querés eliminar "${carritoEliminar?.titulo ?? "este carrito"}"? Esta acción no se puede deshacer.`}
        onClose={() => setCarritoAEliminar(null)}
        secondaryAction={{ label: "Cancelar", onClick: () => setCarritoAEliminar(null) }}
        primaryAction={{
          label: eliminarMutation.isPending ? "Eliminando..." : "Eliminar",
          onClick: () => {
            if (carritoAEliminar !== null) eliminarMutation.mutate(carritoAEliminar);
          },
          variant: "destructive",
        }}
      />
    </main>
  );
}
