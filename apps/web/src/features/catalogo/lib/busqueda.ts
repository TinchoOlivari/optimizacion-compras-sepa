export const MIN_CARACTERES_BUSQUEDA_NOMBRE = 4;

export function esEan13(query: string): boolean {
  return /^\d{13}$/.test(query);
}

export function busquedaHabilitada(query: string): boolean {
  const q = query.trim();
  if (!q) return false;
  if (!esEan13(q) && q.length < MIN_CARACTERES_BUSQUEDA_NOMBRE) return false;
  return true;
}
