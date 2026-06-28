export function formatearARS(valor: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(valor);
}

export function formatearFechaCarrito(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;

  const ahora = new Date();
  const inicioHoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());
  const inicioFecha = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  const diffDias = Math.round((inicioHoy.getTime() - inicioFecha.getTime()) / 86_400_000);

  const hora = new Intl.DateTimeFormat("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(fecha);

  if (diffDias === 0) return `Hoy, ${hora} hs`;
  if (diffDias === 1) return `Ayer, ${hora} hs`;

  return new Intl.DateTimeFormat("es-AR", {
    day: "numeric",
    month: "short",
    year: fecha.getFullYear() !== ahora.getFullYear() ? "numeric" : undefined,
  }).format(fecha);
}
