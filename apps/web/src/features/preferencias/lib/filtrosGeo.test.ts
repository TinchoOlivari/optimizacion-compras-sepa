import { describe, expect, it } from "vitest";

import {
  filtrosGeoDesdePreferencias,
  filtrosGeoParaDetalleProducto,
  filtrosGeoPorDefecto,
} from "./filtrosGeo";

describe("filtrosGeoDesdePreferencias", () => {
  it("devuelve undefined sin preferencias cargadas", () => {
    expect(filtrosGeoDesdePreferencias(undefined)).toBeUndefined();
  });

  it("expone ubicación por defecto para visitantes anónimos", () => {
    expect(filtrosGeoPorDefecto()).toEqual({
      lat: -31.4175,
      lon: -64.1833,
      radio_km: 5,
    });
  });

  it("usa preferencias guardadas o cae al default", () => {
    expect(filtrosGeoParaDetalleProducto(undefined)).toEqual(filtrosGeoPorDefecto());
    expect(
      filtrosGeoParaDetalleProducto({
        radio_km: 8,
        max_paradas: 2,
        preferencia: "MENOR_PRECIO",
        origen: { latitud: -32.9, longitud: -60.6 },
        por_defecto_aplicado: [],
      }),
    ).toEqual({
      lat: -32.9,
      lon: -60.6,
      radio_km: 8,
    });
  });

  it("mapea origen y radio para detalle de producto", () => {
    expect(
      filtrosGeoDesdePreferencias({
        radio_km: 8,
        max_paradas: 2,
        preferencia: "MENOR_PRECIO",
        origen: { latitud: -31.4175, longitud: -64.1833 },
        por_defecto_aplicado: [],
      }),
    ).toEqual({
      lat: -31.4175,
      lon: -64.1833,
      radio_km: 8,
    });
  });
});
