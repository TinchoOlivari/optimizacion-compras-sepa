import { describe, expect, it } from "vitest";

import { busquedaHabilitada, esEan13 } from "./busqueda";

describe("busqueda", () => {
  it("detecta EAN-13 válido", () => {
    expect(esEan13("7790742300101")).toBe(true);
    expect(esEan13("779074230010")).toBe(false);
    expect(esEan13("leche")).toBe(false);
  });

  it("habilita búsqueda con EAN o al menos 4 caracteres", () => {
    expect(busquedaHabilitada("")).toBe(false);
    expect(busquedaHabilitada("  ")).toBe(false);
    expect(busquedaHabilitada("le")).toBe(false);
    expect(busquedaHabilitada("lec")).toBe(false);
    expect(busquedaHabilitada("lech")).toBe(true);
    expect(busquedaHabilitada("  leche  ")).toBe(true);
    expect(busquedaHabilitada("7790742300101")).toBe(true);
  });
});
