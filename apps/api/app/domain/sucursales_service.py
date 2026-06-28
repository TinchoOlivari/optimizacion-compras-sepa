import math

from app.domain.ports import ISucursalesRepository, SucursalGeo

RADIO_KM_DEFAULT = 10
RADIO_KM_MIN = 1
RADIO_KM_MAX = 50


class SucursalesError(Exception):
    pass


class SucursalesValidationError(SucursalesError):
    pass


class SucursalesService:
    def __init__(self, sucursales_repo: ISucursalesRepository) -> None:
        self._sucursales_repo = sucursales_repo

    def get_sucursales_cercanas(
        self,
        lat: float,
        lon: float,
        radio_km: int | None = None,
    ) -> list[SucursalGeo]:
        radio_normalizado = radio_km if radio_km is not None else RADIO_KM_DEFAULT
        self._validar_latitud(lat)
        self._validar_longitud(lon)
        self._validar_radio(radio_normalizado)

        return self._sucursales_repo.sucursales_cercanas(lat, lon, radio_normalizado)

    @staticmethod
    def _validar_latitud(lat: float) -> None:
        if not math.isfinite(lat) or lat < -90 or lat > 90:
            raise SucursalesValidationError("La latitud debe estar entre -90 y 90.")

    @staticmethod
    def _validar_longitud(lon: float) -> None:
        if not math.isfinite(lon) or lon < -180 or lon > 180:
            raise SucursalesValidationError("La longitud debe estar entre -180 y 180.")

    @staticmethod
    def _validar_radio(radio_km: int) -> None:
        if radio_km < RADIO_KM_MIN or radio_km > RADIO_KM_MAX:
            raise SucursalesValidationError("El radio debe estar entre 1 y 50 km.")
