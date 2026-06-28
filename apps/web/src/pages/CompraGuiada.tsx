import type React from "react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Modal } from "@/components/Modal";
import { ParadaCompraCard } from "@/features/compra-guiada/components/ParadaCompraCard";
import { useCompraGuiadaViewModel } from "@/features/compra-guiada/hooks/useCompraGuiadaViewModel";

export default function CompraGuiadaPage(): React.ReactElement {
  const navigate = useNavigate();
  const params = useParams();
  const [modalInterrumpir, setModalInterrumpir] = useState(false);
  const compraGuiadaId = params.id ? Number(params.id) : null;
  const idValido = compraGuiadaId != null && Number.isInteger(compraGuiadaId) && compraGuiadaId > 0;
  const {
    compra,
    query,
    pendientes,
    progreso,
    resueltos,
    totalItems,
    actualizarEstado,
    finalizar,
    finalizando,
  } = useCompraGuiadaViewModel(idValido ? compraGuiadaId : null, () =>
    navigate("/carrito", { replace: true }),
  );

  if (!idValido) {
    return <EstadoPantalla titulo="Compra guiada" mensaje="El carrito indicado no es válido." />;
  }

  if (query.isPending) {
    return (
      <main className="mx-auto max-w-3xl px-3 py-4 pb-24 sm:px-4">
        <VolverButton onClick={() => navigate(-1)} />
        <div className="h-28 animate-pulse rounded-2xl bg-muted" />
        <div className="mt-4 space-y-3">
          <div className="h-44 animate-pulse rounded-2xl bg-muted" />
          <div className="h-44 animate-pulse rounded-2xl bg-muted" />
        </div>
      </main>
    );
  }

  if (query.isError || !compra) {
    return (
      <main className="mx-auto max-w-3xl px-3 py-4 pb-24 sm:px-4">
        <VolverButton onClick={() => navigate(-1)} />
        <section className="rounded-2xl border border-error/20 bg-error-light p-5 shadow-sm">
          <h1 className="text-xl font-semibold text-text-primary">Compra guiada</h1>
          <p className="mt-2 text-sm text-text-secondary">
            No se pudo cargar la distribución vigente para este carrito.
          </p>
          <Button type="button" onClick={() => void query.refetch()} className="mt-5">
            Reintentar
          </Button>
        </section>
      </main>
    );
  }

  const hayPendientes = pendientes > 0;

  function handleFinalizar(): void {
    if (hayPendientes) {
      setModalInterrumpir(true);
      return;
    }
    finalizar(false);
  }

  function confirmarInterrupcion(): void {
    setModalInterrumpir(false);
    finalizar(true);
  }

  return (
    <main className="mx-auto max-w-3xl px-3 py-4 pb-24 sm:px-4">
      <VolverButton onClick={() => navigate(-1)} />

      <header className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              En recorrido
            </p>
            <h1 className="mt-1 text-xl font-semibold text-text-primary">Compra guiada</h1>
          </div>
          <p className="rounded-full bg-primary-light px-3 py-1 text-sm font-semibold text-primary">
            {resueltos}/{totalItems}
          </p>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${progreso}%` }}
          />
        </div>
        <p className="mt-2 text-sm font-semibold text-text-secondary">
          {pendientes === 0
            ? "Sin pendientes"
            : `${pendientes} pendiente${pendientes === 1 ? "" : "s"}`}
        </p>
      </header>

      <section aria-label="Paradas de compra" className="mt-4 space-y-3">
        {compra.paradas.map((parada) => (
          <ParadaCompraCard
            key={parada.sucursalId}
            parada={parada}
            onEstadoChange={actualizarEstado}
          />
        ))}
      </section>

      <footer className="fixed inset-x-0 bottom-0 border-t border-border bg-surface/95 px-3 py-3 shadow-[0_-8px_20px_rgba(0,0,0,0.06)] backdrop-blur sm:px-4">
        <div className="mx-auto max-w-3xl">
          {hayPendientes ? (
            <Button
              type="button"
              variant="destructive"
              className="w-full"
              disabled={finalizando}
              onClick={handleFinalizar}
            >
              {finalizando ? "Finalizando..." : "Interrumpir compra"}
            </Button>
          ) : (
            <Button
              type="button"
              className="w-full"
              disabled={finalizando}
              onClick={handleFinalizar}
            >
              {finalizando ? "Finalizando..." : "Finalizar compra"}
            </Button>
          )}
        </div>
      </footer>

      <Modal
        open={modalInterrumpir}
        title="¿Interrumpir la compra?"
        description={`Tenés ${pendientes} producto${pendientes === 1 ? "" : "s"} pendiente${pendientes === 1 ? "" : "s"}. La compra quedará registrada como interrumpida con el progreso actual.`}
        onClose={() => setModalInterrumpir(false)}
        primaryAction={{
          label: "Interrumpir compra",
          variant: "destructive",
          onClick: confirmarInterrupcion,
        }}
        secondaryAction={{
          label: "Cancelar",
          onClick: () => setModalInterrumpir(false),
        }}
      />
    </main>
  );
}

function VolverButton({ onClick }: { onClick: () => void }): React.ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-3 inline-flex min-h-[38px] items-center gap-2 rounded-full border border-border bg-surface px-3 text-sm font-medium text-secondary shadow-sm hover:bg-muted"
    >
      <span aria-hidden="true">←</span>
      Volver
    </button>
  );
}

function EstadoPantalla({
  titulo,
  mensaje,
}: {
  titulo: string;
  mensaje: string;
}): React.ReactElement {
  return (
    <main className="mx-auto max-w-3xl px-3 py-4 pb-24 sm:px-4">
      <section className="rounded-2xl border border-error/20 bg-error-light p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-text-primary">{titulo}</h1>
        <p className="mt-2 text-sm text-text-secondary">{mensaje}</p>
      </section>
    </main>
  );
}
