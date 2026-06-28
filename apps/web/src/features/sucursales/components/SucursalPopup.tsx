import type { SucursalMapa } from "@/features/sucursales/api/sucursalesApi";

interface SucursalPopupProps {
  sucursal: SucursalMapa;
}

export default function SucursalPopup({ sucursal }: SucursalPopupProps) {
  const ubicacion = [sucursal.localidad, sucursal.provincia].filter(Boolean).join(", ");

  return (
    <article className="min-w-48 space-y-1 text-sm text-text-primary">
      <h3 className="font-bold text-secondary">
        {sucursal.nombre ?? "Sucursal sin nombre"}
      </h3>
      <p>{sucursal.direccion ?? "Dirección no disponible"}</p>
      {ubicacion ? <p className="text-secondary">{ubicacion}</p> : null}
      {sucursal.comercioMarca ? (
        <p className="text-secondary">Comercio: {sucursal.comercioMarca}</p>
      ) : null}
      {sucursal.distanciaKm !== null ? (
        <p className="font-semibold text-primary">
          {sucursal.distanciaKm.toFixed(2)} km de tu ubicación
        </p>
      ) : null}
    </article>
  );
}
