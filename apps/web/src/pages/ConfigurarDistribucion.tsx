"use client";

import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/Button";
import { useCarritoActivo } from "@/features/carrito/hooks/useCarritoActivo";
import { carritoQueryKeys } from "@/features/carrito/lib/queryKeys";
import FormularioConfiguracionOptimizacion from "@/features/preferencias/components/FormularioConfiguracionOptimizacion";
import { usePreferencias } from "@/features/preferencias/hooks/usePreferencias";
import {
  VALORES_INICIALES_FORM,
  type PerfilFormFields,
  camposDesdePreferencias,
  validarFormulario,
} from "@/features/preferencias/lib/form";
import { useSucursales } from "@/features/sucursales/hooks/useSucursales";
import { distribuirCarrito } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useToastStore } from "@/store/toastStore";

export default function ConfigurarDistribucionPage(): React.ReactElement {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useToastStore((state) => state.addToast);
  const autenticado = !!useAuthStore((state) => state.usuario);

  const preferenciasQuery = usePreferencias();
  const carritoQuery = useCarritoActivo(autenticado);

  const [formValues, setFormValues] = useState<PerfilFormFields>({
    radioKm: String(VALORES_INICIALES_FORM.radio_km),
    maxParadas: String(VALORES_INICIALES_FORM.max_paradas),
    preferencia: VALORES_INICIALES_FORM.preferencia,
    latitud: String(VALORES_INICIALES_FORM.latitud),
    longitud: String(VALORES_INICIALES_FORM.longitud),
    direccion: VALORES_INICIALES_FORM.direccion,
    modalidad: VALORES_INICIALES_FORM.modalidad,
  });
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [cargadoDesdePerfil, setCargadoDesdePerfil] = useState(false);

  useEffect(() => {
    if (!preferenciasQuery.data || cargadoDesdePerfil) return;
    setFormValues(camposDesdePreferencias(preferenciasQuery.data));
    setCargadoDesdePerfil(true);
  }, [preferenciasQuery.data, cargadoDesdePerfil]);

  const latitud = Number(formValues.latitud);
  const longitud = Number(formValues.longitud);
  const radioKmNumero = Number(formValues.radioKm);
  const radioKmMapa = Number.isFinite(radioKmNumero)
    ? Math.min(Math.max(radioKmNumero, 1), 50)
    : VALORES_INICIALES_FORM.radio_km;

  const centroMapa = useMemo<[number, number] | null>(() => {
    if (!Number.isFinite(latitud) || !Number.isFinite(longitud)) return null;
    return [latitud, longitud];
  }, [latitud, longitud]);

  const sucursalesQuery = useSucursales(centroMapa?.[0], centroMapa?.[1], radioKmMapa);

  const distribuirMutation = useMutation({
    mutationFn: async () => {
      const carrito = carritoQuery.data;
      if (!carrito) throw new Error("No tenés un carrito activo.");
      return distribuirCarrito(carrito.id, {
        radio_km: Number(formValues.radioKm),
        max_paradas: Number(formValues.maxParadas),
        preferencia: formValues.preferencia,
        ubicacion_referencia: {
          latitud: Number(formValues.latitud),
          longitud: Number(formValues.longitud),
          direccion: formValues.direccion,
          modalidad: formValues.modalidad,
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: carritoQueryKeys.activo() });
      void queryClient.invalidateQueries({ queryKey: carritoQueryKeys.distribucion() });
      navigate("/distribucion");
    },
    onError: () => {
      addToast({
        message: "No pudimos distribuir el carrito. Intentá de nuevo.",
        variant: "error",
      });
    },
  });

  const handleFormChange = useCallback((nuevosValores: PerfilFormFields) => {
    setFormValues(nuevosValores);
    setErrores({});
  }, []);

  const handleDistribuir = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setErrores({});

      const validacion = validarFormulario(formValues);
      if (!validacion.ok) {
        setErrores(validacion.errores);
        addToast({ message: "Revisá los campos marcados.", variant: "error" });
        return;
      }

      await distribuirMutation.mutateAsync();
    },
    [formValues, distribuirMutation, addToast],
  );

  const sinSucursales =
    !sucursalesQuery.isLoading &&
    !sucursalesQuery.isError &&
    (sucursalesQuery.data?.length ?? 0) === 0;

  if (preferenciasQuery.isLoading && !preferenciasQuery.data) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 pb-10">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="mt-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 w-full animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 pb-16">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="mb-6 inline-flex min-h-[44px] items-center gap-2 rounded-full border border-border bg-surface px-4 text-sm font-semibold text-secondary shadow-sm hover:bg-muted"
      >
        <span aria-hidden="true">←</span>
        Volver
      </button>
      <h1 className="mb-2 text-3xl font-bold text-text-primary">Configurar distribución</h1>
      <p className="mb-8 text-text-secondary">
        Ajustá los parámetros para esta distribución. No se guardan en tu perfil.
      </p>

      <form
        onSubmit={(event) => void handleDistribuir(event)}
        className="rounded-xl border border-border bg-surface p-6 shadow-sm"
      >
        <FormularioConfiguracionOptimizacion
          value={formValues}
          onChange={handleFormChange}
          sucursales={sucursalesQuery.data ?? []}
          loading={sucursalesQuery.isLoading && !sucursalesQuery.data}
          error={sucursalesQuery.error}
          onRetry={() => void sucursalesQuery.refetch()}
          errores={errores}
        />

        {sinSucursales ? (
          <p className="mt-4 rounded-lg bg-muted px-4 py-3 text-sm text-secondary">
            No hay sucursales en este radio. Probá ampliar el radio o cambiar la ubicación.
          </p>
        ) : null}

        <div className="mt-8 border-t border-border pt-4 text-right">
          <Button type="submit" disabled={distribuirMutation.isPending || sinSucursales}>
            {distribuirMutation.isPending ? "Distribuyendo..." : "Distribuir carrito ›"}
          </Button>
        </div>
      </form>
    </main>
  );
}
