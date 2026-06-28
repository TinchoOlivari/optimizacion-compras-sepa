import { PreferenciaOptimizacion } from "@tfg/shared";
import { describe, expect, it } from "vitest";

import {
  camposDesdePreferencias,
  payloadDesdeFormulario,
  validarFormulario,
} from "./form";

describe("form preferencias", () => {
  it("mapea preferencias de la API a campos del formulario", () => {
    const campos = camposDesdePreferencias({
      radio_km: 10,
      max_paradas: 4,
      preferencia: PreferenciaOptimizacion.BALANCEADO,
      origen: {
        latitud: -32.9,
        longitud: -60.6,
        direccion: "San Lorenzo 123",
        modalidad: "PUNTO_EN_MAPA",
      },
      por_defecto_aplicado: [],
    });

    expect(campos.radioKm).toBe("10");
    expect(campos.maxParadas).toBe("4");
    expect(campos.preferencia).toBe(PreferenciaOptimizacion.BALANCEADO);
    expect(campos.latitud).toBe("-32.9");
    expect(campos.longitud).toBe("-60.6");
    expect(campos.direccion).toBe("San Lorenzo 123");
    expect(campos.modalidad).toBe("PUNTO_EN_MAPA");
  });

  it("genera etiqueta de coordenadas si la API no devuelve direccion", () => {
    const campos = camposDesdePreferencias({
      radio_km: 5,
      max_paradas: 3,
      preferencia: PreferenciaOptimizacion.MENOR_PRECIO,
      origen: { latitud: -31.4175, longitud: -64.1833 },
      por_defecto_aplicado: [],
    });

    expect(campos.direccion).toBe("Lat: -31.417500, Lon: -64.183300");
  });

  it("rechaza radio y paradas fuera de rango", () => {
    const resultado = validarFormulario({
      radioKm: "0",
      maxParadas: "6",
      preferencia: PreferenciaOptimizacion.MENOR_PRECIO,
      latitud: "-31.4",
      longitud: "-64.1",
      direccion: "Córdoba",
      modalidad: "DIRECCION",
    });

    expect(resultado.ok).toBe(false);
    expect(resultado.errores.radio_km).toBeDefined();
    expect(resultado.errores.max_paradas).toBeDefined();
  });

  it("genera payload válido para la API", () => {
    const payload = payloadDesdeFormulario({
      radioKm: "5",
      maxParadas: "3",
      preferencia: PreferenciaOptimizacion.MENOR_PRECIO,
      latitud: "-31.4175",
      longitud: "-64.1833",
      direccion: "Av. Colón 4747",
      modalidad: "DIRECCION",
    });

    expect(payload).toEqual({
      radio_km: 5,
      max_paradas: 3,
      modo_preferencia: PreferenciaOptimizacion.MENOR_PRECIO,
      ubicacion_referencia: {
        latitud: -31.4175,
        longitud: -64.1833,
        direccion: "Av. Colón 4747",
        modalidad: "DIRECCION",
      },
    });
  });
});
