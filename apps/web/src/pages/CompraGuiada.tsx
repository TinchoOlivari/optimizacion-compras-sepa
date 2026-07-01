import type React from "react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Modal } from "@/components/Modal";
import { ParadaCompraCard } from "@/features/compra-guiada/components/ParadaCompraCard";
import { useCompraGuiadaViewModel } from "@/features/compra-guiada/hooks/useCompraGuiadaViewModel";
import { formatearARS } from "@/lib/format";

export default function CompraGuiadaPage(): React.ReactElement {
  const navigate = useNavigate();
  const params = useParams();
  const [modalInterrumpir, setModalInterrumpir] = useState(false);
  const [precioAlternativaSeleccionada, setPrecioAlternativaSeleccionada] = useState<number | null>(null);
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
    actualizandoItemId,
    alternativasPendientes,
    resolverAlternativa,
    resolviendoAlternativa,
    cerrarPropuestaAlternativa,
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
  const alternativasFaltante = alternativasPendientes?.alternativas ?? [];
  const alternativaSeleccionada =
    alternativasFaltante.find((alternativa) => alternativa.precio_id === precioAlternativaSeleccionada) ??
    alternativasFaltante[0] ??
    null;

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
            actualizandoItemId={actualizandoItemId}
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

      <Modal
        open={alternativasPendientes != null}
        title="Resolver producto faltante"
        description={
          alternativaSeleccionada
            ? `${alternativaSeleccionada.nombre_producto} está disponible en estas sucursales. Elegí la que más te convenga o conservá el recorrido original.`
            : ""
        }
        onClose={() => {
          setPrecioAlternativaSeleccionada(null);
          cerrarPropuestaAlternativa();
        }}
        primaryAction={{
          label: resolviendoAlternativa ? "Agregando..." : "Agregar parada",
          onClick: () => {
            if (alternativaSeleccionada) {
              resolverAlternativa(alternativaSeleccionada.precio_id, true);
              setPrecioAlternativaSeleccionada(null);
            }
          },
        }}
        secondaryAction={{
          label: "No ir",
          onClick: () => {
            if (alternativaSeleccionada) {
              resolverAlternativa(alternativaSeleccionada.precio_id, false);
              setPrecioAlternativaSeleccionada(null);
            }
          },
        }}
      >
        <div className="mt-3 space-y-1">
          {alternativasFaltante.map((alternativa) => {
            const seleccionada = alternativa.precio_id === alternativaSeleccionada?.precio_id;
            return (
              <button
                key={alternativa.precio_id}
                type="button"
                onClick={() => setPrecioAlternativaSeleccionada(alternativa.precio_id)}
                className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition ${
                  seleccionada
                    ? "border-primary bg-primary-light/40"
                    : "border-border bg-muted/30 hover:bg-muted"
                }`}
              >
                <div
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                    seleccionada
                      ? "border-primary bg-primary"
                      : "border-border bg-surface"
                  }`}
                >
                  {seleccionada && (
                    <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-text-primary">{alternativa.sucursal}</p>
                  <p className="truncate text-xs text-text-secondary">
                    {formatearDireccionCorta(alternativa)}
                  </p>
                  <p
                    className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      alternativa.esta_en_recorrido
                        ? "bg-success-light text-success"
                        : "bg-accent-light text-accent-hover"
                    }`}
                  >
                    {alternativa.esta_en_recorrido
                      ? "Ya está en tu recorrido"
                      : "Requiere parada nueva"}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-sm font-semibold text-text-primary">
                    {formatearARS(alternativa.subtotal)}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {alternativa.distancia_km != null
                      ? `${alternativa.distancia_km.toFixed(1)} km`
                      : "—"}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </Modal>
    </main>
  );
}

function formatearDireccionCorta({
  direccion,
  localidad,
}: {
  direccion: string | null;
  localidad: string | null;
}): string {
  const partes = [direccion, localidad].filter(Boolean);
  return partes.length > 0 ? partes.join(", ") : "dirección no informada";
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
