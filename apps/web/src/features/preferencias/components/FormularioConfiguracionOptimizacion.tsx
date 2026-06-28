import { useCallback, useMemo } from "react";

import { ModalidadUbicacion } from "@tfg/shared";

import MapaUbicacion, {
  type MapaUbicacionValue,
} from "@/features/ubicacion/components/MapaUbicacion";
import type { SucursalMapa } from "@/features/sucursales/api/sucursalesApi";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";

import {
  PREFERENCIAS_OPCIONES,
  VALORES_INICIALES_FORM,
  type PerfilFormFields,
} from "../lib/form";

const MAPA_RADIO_DEBOUNCE_MS = 300;

export interface FormularioConfiguracionOptimizacionProps {
  value: PerfilFormFields;
  onChange: (value: PerfilFormFields) => void;
  sucursales: SucursalMapa[];
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  errores?: Record<string, string>;
}

export default function FormularioConfiguracionOptimizacion({
  value,
  onChange,
  sucursales,
  loading = false,
  error = null,
  onRetry,
  errores = {},
}: FormularioConfiguracionOptimizacionProps) {
  const radioKmNumero = Number(value.radioKm);
  const radioKmMapa = Number.isFinite(radioKmNumero)
    ? Math.min(Math.max(radioKmNumero, 1), 50)
    : VALORES_INICIALES_FORM.radio_km;
  const radioKmDebounced = useDebouncedValue(radioKmMapa, MAPA_RADIO_DEBOUNCE_MS);

  const mapaUbicacionValue: MapaUbicacionValue = useMemo(
    () => ({
      latitud: Number(value.latitud) || VALORES_INICIALES_FORM.latitud,
      longitud: Number(value.longitud) || VALORES_INICIALES_FORM.longitud,
      direccion: value.direccion || "",
      modalidad: (value.modalidad as ModalidadUbicacion) || ModalidadUbicacion.DIRECCION,
    }),
    [value.latitud, value.longitud, value.direccion, value.modalidad],
  );

  const handleMapaChange = useCallback(
    (nuevoValor: MapaUbicacionValue) => {
      onChange({
        ...value,
        latitud: String(nuevoValor.latitud),
        longitud: String(nuevoValor.longitud),
        direccion: nuevoValor.direccion,
        modalidad: nuevoValor.modalidad,
      });
    },
    [onChange, value],
  );

  return (
    <>
      <div className="mb-6">
        <label className="mb-2 block text-sm font-bold text-text-primary">
          ⊙ Ubicación de referencia
        </label>
        <MapaUbicacion
          value={mapaUbicacionValue}
          onChange={handleMapaChange}
          sucursales={sucursales}
          radioKm={radioKmDebounced}
          sucursalesLoading={loading}
          sucursalesError={error}
          onRetry={onRetry ?? (() => {})}
        />
        {errores.ubicacion ? (
          <p className="mt-2 text-sm text-error">{errores.ubicacion}</p>
        ) : null}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <label htmlFor="radio_km" className="mb-2 block text-sm font-bold text-text-primary">
            Radio máximo: {radioKmMapa} km
          </label>
          <input
            id="radio_km"
            name="radio_km"
            type="range"
            min={1}
            max={50}
            required
            value={value.radioKm}
            onChange={(event) => onChange({ ...value, radioKm: event.target.value })}
            className="h-2 w-full cursor-pointer accent-primary"
            aria-invalid={!!errores.radio_km}
            aria-valuetext={`${radioKmMapa} kilómetros`}
          />
          <div className="mt-2 flex justify-between text-xs text-secondary" aria-hidden="true">
            <span>1 km</span>
            <span>50 km</span>
          </div>
          {errores.radio_km ? (
            <p className="mt-2 text-sm text-error">{errores.radio_km}</p>
          ) : null}
        </div>

        <div>
          <label htmlFor="max_paradas" className="mb-2 block text-sm font-bold text-text-primary">
            Máximo de paradas
          </label>
          <input
            id="max_paradas"
            name="max_paradas"
            type="number"
            min={1}
            max={5}
            required
            value={value.maxParadas}
            onChange={(event) => onChange({ ...value, maxParadas: event.target.value })}
            className="min-h-[44px] w-full rounded-xl border border-border bg-background px-3 text-base text-text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            aria-invalid={!!errores.max_paradas}
          />
          {errores.max_paradas ? (
            <p className="mt-2 text-sm text-error">{errores.max_paradas}</p>
          ) : null}
        </div>
      </div>

      <fieldset className="mt-6">
        <legend className="mb-3 text-sm font-bold text-text-primary">Preferencia</legend>
        <div className="space-y-3">
          {PREFERENCIAS_OPCIONES.map((opcion) => (
            <label key={opcion.value} className="flex items-center gap-3 text-base font-medium text-text-primary">
              <input
                type="radio"
                name="modo_preferencia"
                value={opcion.value}
                checked={value.preferencia === opcion.value}
                onChange={(event) => onChange({ ...value, preferencia: event.target.value })}
                className="h-4 w-4 accent-secondary"
              />
              {opcion.label}
            </label>
          ))}
        </div>
        {errores.modo_preferencia ? (
          <p className="mt-2 text-sm text-error">{errores.modo_preferencia}</p>
        ) : null}
      </fieldset>
    </>
  );
}
