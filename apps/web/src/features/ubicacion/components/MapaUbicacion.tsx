import { useCallback, useMemo, useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

import "leaflet/dist/leaflet.css";
import "@/features/sucursales/components/mapa-smooth.css";

import { ModalidadUbicacion } from "@tfg/shared";

import type { SucursalMapa } from "@/features/sucursales/api/sucursalesApi";
import { crearIconoLogo } from "@/features/sucursales/lib/iconoLogo";
import SucursalPopup from "@/features/sucursales/components/SucursalPopup";
import { Button } from "@/components/Button";
import { useToastStore } from "@/store/toastStore";

const ICONO_UBICACION = L.divIcon({
  className: "marcador-ubicacion",
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -18],
  html: `<div class="marcador-ubicacion-pulso"></div><div class="marcador-ubicacion-inner"></div>`,
});

const TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const CENTRO_DEFECTO: [number, number] = [-31.4175, -64.1833];
const ZOOM_DEFECTO = 13;

function zoomDesdeRadio(radioKm: number): number {
  if (radioKm <= 3) return 13;
  if (radioKm <= 8) return 12;
  if (radioKm <= 20) return 11;
  return 10;
}

function ClickEnMapa({ onClick }: { onClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(event) {
      const { lat, lng } = event.latlng;
      onClick(lat, lng);
    },
  });
  return null;
}

function AjustarVista({ radioKm }: { radioKm: number }) {
  const map = useMap();
  const mapRef = useRef(map);
  mapRef.current = map;

  useEffect(() => {
    const zoom = zoomDesdeRadio(radioKm);
    mapRef.current.setZoom(zoom, { animate: true });
  }, [radioKm]);

  return null;
}

export interface MapaUbicacionValue {
  latitud: number;
  longitud: number;
  direccion: string;
  modalidad: ModalidadUbicacion;
}

interface MapaUbicacionProps {
  value: MapaUbicacionValue;
  onChange: (value: MapaUbicacionValue) => void;
  sucursales: SucursalMapa[];
  radioKm: number;
  sucursalesLoading: boolean;
  sucursalesError: Error | null;
  onRetry: () => void;
  mostrarCoordenadas?: boolean;
}

export default function MapaUbicacion({
  value,
  onChange,
  sucursales,
  radioKm,
  sucursalesLoading,
  sucursalesError,
  onRetry,
  mostrarCoordenadas = false,
}: MapaUbicacionProps) {
  const addToast = useToastStore((state) => state.addToast);
  const [keyMapa, setKeyMapa] = useState(0);
  const [geoError, setGeoError] = useState<string | null>(null);

  const centro = useMemo((): [number, number] => {
    if (Number.isFinite(value.latitud) && Number.isFinite(value.longitud)) {
      return [value.latitud, value.longitud];
    }
    return CENTRO_DEFECTO;
  }, [value.latitud, value.longitud]);

  const tieneCoordenadas =
    Number.isFinite(value.latitud) && Number.isFinite(value.longitud);

  const handleClickMapa = useCallback(
    (lat: number, lon: number) => {
      onChange({
        latitud: lat,
        longitud: lon,
        direccion: `Lat: ${lat.toFixed(6)}, Lon: ${lon.toFixed(6)}`,
        modalidad: ModalidadUbicacion.PUNTO_EN_MAPA,
      });
    },
    [onChange],
  );

  const handleDragMarcador = useCallback(
    (event: L.LeafletEvent) => {
      const marker = event.target as L.Marker;
      const pos = marker.getLatLng();
      onChange({
        latitud: pos.lat,
        longitud: pos.lng,
        direccion: `Lat: ${pos.lat.toFixed(6)}, Lon: ${pos.lng.toFixed(6)}`,
        modalidad: ModalidadUbicacion.PUNTO_EN_MAPA,
      });
    },
    [onChange],
  );

  const handleGeolocalizacion = useCallback(() => {
    if (!navigator.geolocation) {
      setGeoError("Tu navegador no soporta geolocalización.");
      return;
    }

    setGeoError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        onChange({
          latitud: lat,
          longitud: lon,
          direccion: "Ubicación actual",
          modalidad: ModalidadUbicacion.GEOLOCALIZACION,
        });
        setKeyMapa((k) => k + 1);
        addToast({ message: "Ubicación actual detectada.", variant: "success" });
      },
      (error) => {
        let mensaje = "No pudimos obtener tu ubicación.";
        if (error.code === error.PERMISSION_DENIED) {
          mensaje = "Permiso de ubicación denegado. Revisá la configuración del navegador.";
        }
        setGeoError(mensaje);
        addToast({ message: mensaje, variant: "error" });
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, [onChange, addToast]);

  const iconosPorId = useMemo(() => {
    const cache = new Map<number, L.Icon>();
    for (const s of sucursales) {
      if (!cache.has(s.id)) {
        cache.set(s.id, crearIconoLogo(logoUrlSucursal(s)));
      }
    }
    return cache;
  }, [sucursales]);

  if (sucursalesError) {
    return (
      <div className="space-y-2">
        <div className="h-80 w-full rounded-xl border border-border bg-muted flex items-center justify-center">
          <div className="text-center text-sm text-text-primary">
            <p className="font-semibold text-error">No pudimos cargar las sucursales.</p>
            <p className="mt-1 text-secondary">Intentá nuevamente en unos segundos.</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
            >
              Reintentar
            </button>
          </div>
        </div>
        {mostrarCoordenadas && tieneCoordenadas ? (
          <div className="flex items-center gap-2 rounded-lg bg-muted px-4 py-2 text-sm text-secondary">
            <span aria-hidden="true">📍</span>
            <span>
              Lat: {value.latitud.toFixed(6)}, Lon: {value.longitud.toFixed(6)}
            </span>
            <span className="mx-1 text-border">|</span>
            <span className="truncate">{value.direccion}</span>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="relative h-80 w-full overflow-hidden rounded-xl border border-border">
        <MapContainer
          key={keyMapa}
          center={centro}
          zoom={ZOOM_DEFECTO}
          scrollWheelZoom
          zoomAnimation
          className="h-full w-full"
        >
          <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} subdomains="abcd" />
          <ClickEnMapa onClick={handleClickMapa} />
          <AjustarVista radioKm={radioKm} />

          {tieneCoordenadas ? (
            <>
              <Circle
                center={centro}
                radius={radioKm * 1000}
                pathOptions={{
                  color: "#0F766E",
                  fillColor: "#0F766E",
                  fillOpacity: 0.1,
                  weight: 0.5,
                }}
              />
              <Marker
                position={centro}
                draggable
                icon={ICONO_UBICACION}
                eventHandlers={{ dragend: handleDragMarcador }}
              >
                <Popup>Arrastrá el marcador para ajustar la ubicación</Popup>
              </Marker>
            </>
          ) : null}

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

        <div className="absolute right-2 top-2 z-[1000]">
          <Button type="button" variant="secondary" onClick={handleGeolocalizacion}>
            📍 Mi ubicación
          </Button>
        </div>

        {sucursalesLoading ? (
          <div className="absolute bottom-2 left-2 z-[1000] rounded bg-white/90 px-2 py-1 text-xs text-secondary">
            Cargando sucursales...
          </div>
        ) : null}
      </div>

      {geoError ? (
        <p className="text-sm text-error">{geoError}</p>
      ) : null}

      {mostrarCoordenadas && tieneCoordenadas ? (
        <div className="flex items-center gap-2 rounded-lg bg-muted px-4 py-2 text-sm text-secondary">
          <span aria-hidden="true">📍</span>
          <span>
            Lat: {value.latitud.toFixed(6)}, Lon: {value.longitud.toFixed(6)}
          </span>
          <span className="mx-1 text-border">|</span>
          <span className="truncate">{value.direccion}</span>
        </div>
      ) : null}

      {!sucursalesLoading && sucursales.length === 0 && tieneCoordenadas ? (
        <p className="rounded-lg bg-muted px-4 py-2 text-sm text-secondary">
          No encontramos sucursales dentro de {radioKm} km. Probá ampliar el radio.
        </p>
      ) : null}
    </div>
  );
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
