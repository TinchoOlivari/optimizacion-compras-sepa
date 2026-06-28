"use client";

import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import FormularioConfiguracionOptimizacion from "@/features/preferencias/components/FormularioConfiguracionOptimizacion";
import { useSucursales } from "@/features/sucursales/hooks/useSucursales";
import { usePreferencias } from "@/features/preferencias/hooks/usePreferencias";
import { usePreferenciasMutations } from "@/features/preferencias/hooks/usePreferenciasMutations";
import {
  VALORES_INICIALES_FORM,
  type PerfilFormFields,
  camposDesdePreferencias,
  payloadDesdeFormulario,
  validarFormulario,
} from "@/features/preferencias/lib/form";
import { useActualizarNombre } from "@/features/usuario/hooks/useActualizarNombre";
import { validarNombre } from "@/lib/validaciones/auth";
import { useAppStore } from "@/store/appStore";
import { useAuthStore } from "@/store/authStore";
import { useToastStore } from "@/store/toastStore";

export default function PerfilPage(): React.ReactElement {
  const navigate = useNavigate();
  const usuario = useAuthStore((state) => state.usuario);
  const logout = useAuthStore((state) => state.logout);
  const sincronizarCarritoLogout = useAppStore((state) => state.sincronizarCarritoLogout);
  const addToast = useToastStore((state) => state.addToast);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [editandoNombre, setEditandoNombre] = useState(false);
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [errorNombre, setErrorNombre] = useState<string | undefined>(undefined);

  const preferenciasQuery = usePreferencias();
  const { guardarMutation } = usePreferenciasMutations();
  const { actualizarMutation } = useActualizarNombre();

  const [formValues, setFormValues] = useState<PerfilFormFields>({
    radioKm: String(VALORES_INICIALES_FORM.radio_km),
    maxParadas: String(VALORES_INICIALES_FORM.max_paradas),
    preferencia: VALORES_INICIALES_FORM.preferencia,
    latitud: String(VALORES_INICIALES_FORM.latitud),
    longitud: String(VALORES_INICIALES_FORM.longitud),
    direccion: VALORES_INICIALES_FORM.direccion,
    modalidad: VALORES_INICIALES_FORM.modalidad,
  });

  const latitudMapa = Number(formValues.latitud);
  const longitudMapa = Number(formValues.longitud);
  const radioKmNumero = Number(formValues.radioKm);
  const radioKmMapa = Number.isFinite(radioKmNumero)
    ? Math.min(Math.max(radioKmNumero, 1), 50)
    : VALORES_INICIALES_FORM.radio_km;
  const centroMapa = useMemo<[number, number] | null>(() => {
    if (!Number.isFinite(latitudMapa) || !Number.isFinite(longitudMapa)) {
      return null;
    }
    return [latitudMapa, longitudMapa];
  }, [latitudMapa, longitudMapa]);
  const sucursalesQuery = useSucursales(
    centroMapa?.[0],
    centroMapa?.[1],
    radioKmMapa,
  );

  useEffect(() => {
    if (!preferenciasQuery.data) return;
    setFormValues(camposDesdePreferencias(preferenciasQuery.data));
  }, [preferenciasQuery.data]);

  const handleFormChange = useCallback((nuevosValores: PerfilFormFields) => {
    setFormValues(nuevosValores);
    setErrores({});
  }, []);

  async function guardarPerfil(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setErrores({});

    const validacion = validarFormulario(formValues);

    if (!validacion.ok) {
      setErrores(validacion.errores);
      addToast({ message: "Revisá los campos marcados.", variant: "error" });
      return;
    }

    await guardarMutation.mutateAsync(payloadDesdeFormulario(formValues));
  }

  function iniciarEdicionNombre(): void {
    setNuevoNombre(usuario?.nombre ?? "");
    setErrorNombre(undefined);
    setEditandoNombre(true);
  }

  function cancelarEdicionNombre(): void {
    setEditandoNombre(false);
    setErrorNombre(undefined);
  }

  async function guardarNombre(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    const error = validarNombre(nuevoNombre);
    if (error) {
      setErrorNombre(error);
      return;
    }

    await actualizarMutation.mutateAsync(nuevoNombre.trim());
    setEditandoNombre(false);
  }

  function cerrarSesion(): void {
    sincronizarCarritoLogout();
    logout();
    navigate("/login");
  }

  if (preferenciasQuery.isLoading && !preferenciasQuery.data) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 pb-10">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="mt-6 space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-32 w-full animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 pb-16">
      <h1 className="mb-8 text-3xl font-bold text-text-primary">Mi Perfil</h1>

      <section className="rounded-xl border border-border bg-surface p-6 shadow-sm" aria-label="Datos de usuario">
        {editandoNombre ? (
          <form onSubmit={(event) => void guardarNombre(event)} className="space-y-3">
            <label htmlFor="nombre" className="block text-sm font-bold text-text-primary">
              Nombre
            </label>
            <div className="flex gap-2">
              <input
                id="nombre"
                name="nombre"
                type="text"
                autoFocus
                value={nuevoNombre}
                onChange={(event) => setNuevoNombre(event.target.value)}
                className="min-h-[44px] w-full rounded-xl border border-border bg-background px-3 text-base text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                aria-invalid={!!errorNombre}
                disabled={actualizarMutation.isPending}
              />
              <Button
                type="submit"
                variant="primary"
                disabled={actualizarMutation.isPending}
              >
                {actualizarMutation.isPending ? "Guardando..." : "Guardar"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={cancelarEdicionNombre}
                disabled={actualizarMutation.isPending}
              >
                Cancelar
              </Button>
            </div>
            {errorNombre ? (
              <p className="text-sm text-error">{errorNombre}</p>
            ) : null}
          </form>
        ) : (
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-secondary">{usuario?.nombre ?? "Usuario"}</h2>
              <button
                type="button"
                onClick={iniciarEdicionNombre}
                className="text-sm font-medium text-primary hover:underline"
              >
                Editar
              </button>
            </div>
            <p className="mt-2 text-text-primary">{usuario?.correo ?? "correo@ejemplo.com"}</p>
          </div>
        )}
      </section>

      <form onSubmit={(event) => void guardarPerfil(event)} className="mt-6 rounded-xl border border-border bg-surface p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-bold text-secondary">⌘ Parámetros de optimización predefinidos</h2>

        <FormularioConfiguracionOptimizacion
          value={formValues}
          onChange={handleFormChange}
          sucursales={sucursalesQuery.data ?? []}
          loading={sucursalesQuery.isLoading && !sucursalesQuery.data}
          error={sucursalesQuery.error}
          onRetry={() => void sucursalesQuery.refetch()}
          errores={errores}
        />

        <div className="mt-8 border-t border-border pt-4 text-right">
          <Button type="submit" disabled={guardarMutation.isPending}>
            {guardarMutation.isPending ? "Guardando..." : "Guardar preferencias"}
          </Button>
        </div>
      </form>

      <div className="mt-14 text-center">
        <button type="button" onClick={cerrarSesion} className="font-semibold text-error hover:underline">
          Cerrar sesión
        </button>
      </div>
    </main>
  );
}
