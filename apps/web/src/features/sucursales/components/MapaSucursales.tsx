import { useEffect, useMemo, useRef } from "react";
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";

import "leaflet/dist/leaflet.css";
import "./mapa-smooth.css";

import type { SucursalMapa } from "@/features/sucursales/api/sucursalesApi";

import { crearIconoLogo } from "../lib/iconoLogo";
import SucursalPopup from "./SucursalPopup";

const TILE_LAYER_URL =
  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE_LAYER_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const ICONO_USUARIO = L.divIcon({
  className: "usuario-dot",
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  popupAnchor: [0, -16],
  html: `<div class="usuario-dot-inner"></div>`,
});

interface MapaSucursalesProps {
  sucursales: SucursalMapa[];
  centro: [number, number];
  radioKm: number;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
}

interface ActualizarVistaProps {
  centro: [number, number];
  radioKm: number;
}

function ActualizarVista({ centro, radioKm }: ActualizarVistaProps) {
  const map = useMap();
  const mapRef = useRef(map);
  mapRef.current = map;

  useEffect(() => {
    const zoom = zoomDesdeRadio(radioKm);
    // Solo reposiciona si cambió centro o radio; ignora cambios internos del mapa
    mapRef.current.setView(centro, zoom, { animate: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- map se usa via ref, no en deps
  }, [centro, radioKm]);

  return null;
}

export default function MapaSucursales({
  sucursales,
  centro,
  radioKm,
  loading,
  error,
  onRetry,
}: MapaSucursalesProps) {
  const zoom = useMemo(() => zoomDesdeRadio(radioKm), [radioKm]);

  // Cache icons by sucursal ID para que no se recreen en cada render
  const iconosPorId = useMemo(() => {
    const cache = new Map<number, L.Icon>();
    for (const s of sucursales) {
      if (!cache.has(s.id)) {
        cache.set(s.id, crearIconoLogo(logoUrlSucursal(s)));
      }
    }
    return cache;
  }, [sucursales]);

  if (loading) {
    return (
      <div className="h-80 w-full animate-pulse rounded-xl border border-border bg-muted" />
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-error/30 bg-error/5 p-4 text-sm text-text-primary">
        <p className="font-semibold text-error">No pudimos cargar las sucursales cercanas.</p>
        <p className="mt-1 text-secondary">Intentá nuevamente en unos segundos.</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="h-80 w-full overflow-hidden rounded-xl border border-border">
        <MapContainer
          center={centro}
          zoom={zoom}
          scrollWheelZoom
          zoomAnimation
          className="h-full w-full"
        >
          <TileLayer
            attribution={TILE_LAYER_ATTRIBUTION}
            url={TILE_LAYER_URL}
            subdomains="abcd"
          />
          <ActualizarVista centro={centro} radioKm={radioKm} />
          <Circle
            center={centro}
            radius={radioKm * 1000}
            pathOptions={{ color: "#0F766E", fillColor: "#0F766E", fillOpacity: 0.1, weight: 0.5 }}
          />

          {/* Marcador de la ubicación del usuario */}
          <Marker position={centro} icon={ICONO_USUARIO}>
            <Popup>📍 Tu ubicación de referencia</Popup>
          </Marker>

          {sucursales.map((sucursal) => (
            <Marker
              key={sucursal.id}
              position={[sucursal.latitud, sucursal.longitud]}
              icon={iconosPorId.get(sucursal.id)}
            >
              <Popup>
                <SucursalPopup sucursal={sucursal} />
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {sucursales.length === 0 ? (
        <p className="rounded-lg bg-muted px-4 py-2 text-sm text-secondary">
          No encontramos sucursales dentro de {radioKm} km. Probá ampliar el radio.
        </p>
      ) : null}
    </div>
  );
}

function zoomDesdeRadio(radioKm: number): number {
  if (radioKm <= 3) return 13;
  if (radioKm <= 8) return 12;
  if (radioKm <= 20) return 11;
  return 10;
}

function logoUrlSucursal(sucursal: SucursalMapa): string {
  if (sucursal.banderaLogoUrl) {
    if (
      sucursal.banderaLogoUrl.startsWith("/") ||
      sucursal.banderaLogoUrl.startsWith("http://") ||
      sucursal.banderaLogoUrl.startsWith("https://")
    ) {
      return sucursal.banderaLogoUrl;
    }
    return `/${sucursal.banderaLogoUrl}`;
  }

  return `/logos/${sucursal.comercioId}.png`;
}
