import json
from typing import Protocol, TypeGuard
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


class IOsrmClient(Protocol):
    def obtener_matriz_km(self, puntos: list[tuple[float, float]]) -> list[list[float]]: ...


class OsrmClient(IOsrmClient):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def obtener_matriz_km(self, puntos: list[tuple[float, float]]) -> list[list[float]]:
        if len(puntos) == 1:
            return [[0.0]]

        coordinates = ";".join(f"{lon},{lat}" for lat, lon in puntos)
        url = f"{self._base_url}/table/v1/driving/{coordinates}?annotations=distance"

        try:
            with urlopen(url, timeout=1.5) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError):
            return self._matriz_haversine(puntos)

        distances = payload.get("distances")
        if not isinstance(distances, list):
            return self._matriz_haversine(puntos)

        if not self._matriz_osrm_valida(distances, len(puntos)):
            return self._matriz_haversine(puntos)

        return [[round(float(value) / 1000.0, 3) for value in row] for row in distances]

    @staticmethod
    def _matriz_osrm_valida(
        distances: list[object], size: int
    ) -> TypeGuard[list[list[int | float]]]:
        if len(distances) != size:
            return False

        for row in distances:
            if not isinstance(row, list) or len(row) != size:
                return False

            if any(value is None or isinstance(value, bool) for value in row):
                return False

            if any(not isinstance(value, int | float) for value in row):
                return False

        return True

    @staticmethod
    def _matriz_haversine(puntos: list[tuple[float, float]]) -> list[list[float]]:
        from math import asin, cos, radians, sin, sqrt

        def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
            lat1, lon1 = radians(a[0]), radians(a[1])
            lat2, lon2 = radians(b[0]), radians(b[1])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            x = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            return 6371.0 * 2 * asin(sqrt(x))

        matriz: list[list[float]] = []
        for origen in puntos:
            fila: list[float] = []
            for destino in puntos:
                fila.append(round(distancia_km(origen, destino), 3))
            matriz.append(fila)
        return matriz
