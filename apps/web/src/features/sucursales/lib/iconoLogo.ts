import L from "leaflet";

import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

const ICONO_DEFECTO = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

class IconoLogo extends L.Icon {
  override createIcon(oldIcon?: HTMLElement): HTMLElement {
    const icon = super.createIcon(oldIcon);

    if (icon instanceof HTMLImageElement) {
      icon.onerror = () => {
        icon.onerror = null;
        icon.src = iconUrl;
        icon.srcset = iconRetinaUrl;
        icon.className = "leaflet-marker-icon";
        icon.style.width = "25px";
        icon.style.height = "41px";
      };
    }

    return icon;
  }
}

export function crearIconoLogo(logoUrl: string | null): L.Icon {
  if (!logoUrl) {
    return ICONO_DEFECTO;
  }

  return new IconoLogo({
    iconUrl: logoUrl,
    iconRetinaUrl: logoUrl,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
    className: "rounded-full border-2 border-white bg-white object-contain",
  });
}
