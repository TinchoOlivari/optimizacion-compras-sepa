import { PreferenciaOptimizacion } from "@tfg/shared";

import type { PreferenciasResponse, UbicacionReferencia } from "@/lib/api";

export const PREFERENCIAS_OPCIONES = [
  { value: PreferenciaOptimizacion.MENOR_PRECIO, label: "Menor precio" },
  { value: PreferenciaOptimizacion.MENOR_DESPLAZAMIENTO, label: "Menor desplazamiento" },
  { value: PreferenciaOptimizacion.BALANCEADO, label: "Balanceado" },
] as const;

export const VALORES_INICIALES_FORM = {
  radio_km: 5,
  max_paradas: 3,
  preferencia: PreferenciaOptimizacion.MENOR_PRECIO,
  latitud: -31.4175,
  longitud: -64.1833,
  direccion: "Av. Colón 4747, X5000 Córdoba",
  modalidad: "DIRECCION",
} as const;

export interface PerfilFormFields {
  radioKm: string;
  maxParadas: string;
  preferencia: string;
  latitud: string;
  longitud: string;
  direccion: string;
  modalidad: string;
}

export interface ValidacionFormularioResult {
  ok: boolean;
  errores: Record<string, string>;
}

export function camposDesdePreferencias(
  preferencias: PreferenciasResponse,
): PerfilFormFields {
  const { latitud, longitud, direccion, modalidad } = preferencias.origen;

  return {
    radioKm: String(preferencias.radio_km),
    maxParadas: String(preferencias.max_paradas),
    preferencia: preferencias.preferencia,
    latitud: String(latitud),
    longitud: String(longitud),
    direccion:
      direccion ??
      `Lat: ${latitud.toFixed(6)}, Lon: ${longitud.toFixed(6)}`,
    modalidad: modalidad ?? VALORES_INICIALES_FORM.modalidad,
  };
}

export function validarFormulario(
  campos: PerfilFormFields,
): ValidacionFormularioResult {
  const radioKmNum = Number(campos.radioKm);
  const maxParadasNum = Number(campos.maxParadas);
  const latitudNum = Number(campos.latitud);
  const longitudNum = Number(campos.longitud);
  const errores: Record<string, string> = {};

  if (!Number.isInteger(radioKmNum) || radioKmNum < 1 || radioKmNum > 50) {
    errores.radio_km = "El radio debe estar entre 1 y 50 km.";
  }

  if (!Number.isInteger(maxParadasNum) || maxParadasNum < 1 || maxParadasNum > 5) {
    errores.max_paradas = "La cantidad de paradas debe estar entre 1 y 5.";
  }

  if (!PREFERENCIAS_OPCIONES.some((opcion) => opcion.value === campos.preferencia)) {
    errores.modo_preferencia = "Seleccioná una preferencia de optimización.";
  }

  if (Number.isNaN(latitudNum) || latitudNum < -90 || latitudNum > 90) {
    errores.ubicacion = "La ubicación no es válida.";
  }

  if (Number.isNaN(longitudNum) || longitudNum < -180 || longitudNum > 180) {
    errores.ubicacion = "La ubicación no es válida.";
  }

  return { ok: Object.keys(errores).length === 0, errores };
}

export function payloadDesdeFormulario(campos: PerfilFormFields): {
  radio_km: number;
  max_paradas: number;
  modo_preferencia: string;
  ubicacion_referencia: UbicacionReferencia;
} {
  return {
    radio_km: Number(campos.radioKm),
    max_paradas: Number(campos.maxParadas),
    modo_preferencia: campos.preferencia,
    ubicacion_referencia: {
      latitud: Number(campos.latitud),
      longitud: Number(campos.longitud),
      direccion: campos.direccion,
      modalidad: campos.modalidad,
    },
  };
}
