from typing import Any

from psycopg.rows import dict_row

from app.domain.ports import ISucursalesRepository, SucursalGeo
from app.infra.db import get_connection


class SucursalesRepository(ISucursalesRepository):
    def __init__(self, connection: Any | None = None) -> None:
        self.connection = connection

    def sucursales_cercanas(self, lat: float, lon: float, radio_km: int) -> list[SucursalGeo]:
        if self.connection is not None:
            return self._sucursales_cercanas_con_connection(lat, lon, radio_km)

        with get_connection() as connection:
            self.connection = connection
            try:
                return self._sucursales_cercanas_con_connection(lat, lon, radio_km)
            finally:
                self.connection = None

    def _sucursales_cercanas_con_connection(
        self,
        lat: float,
        lon: float,
        radio_km: int,
    ) -> list[SucursalGeo]:
        if self.connection is None:
            raise RuntimeError("No hay conexión disponible para consultar sucursales")

        with self.connection.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    COALESCE(s.nombre, c.razon_social) AS nombre,
                    s.direccion,
                    s.localidad,
                    s.provincia,
                    COALESCE(s.latitud, ST_Y(s.geo::geometry)) AS latitud,
                    COALESCE(s.longitud, ST_X(s.geo::geometry)) AS longitud,
                    ST_Distance(
                        s.geo,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) / 1000 AS distancia_km,
                    c.id AS comercio_id,
                    COALESCE(b.nombre, c.razon_social) AS comercio_marca,
                    b.nombre AS bandera_nombre,
                    b.url_logo AS bandera_logo_url
                FROM sucursal s
                JOIN comercio c ON c.id = s.comercio_id
                JOIN bandera b ON b.id = s.bandera_id
                WHERE s.geo IS NOT NULL
                  AND ST_DWithin(
                        s.geo,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s * 1000
                  )
                ORDER BY distancia_km ASC, s.id ASC
                """,
                (lon, lat, lon, lat, radio_km),
            )
            rows = cur.fetchall()
            return [_map_sucursal(row) for row in rows]


def _map_sucursal(row: dict[str, Any]) -> SucursalGeo:
    return SucursalGeo(
        id=int(row["id"]),
        nombre=_optional_str(row.get("nombre")),
        direccion=_optional_str(row.get("direccion")),
        localidad=_optional_str(row.get("localidad")),
        provincia=_optional_str(row.get("provincia")),
        latitud=float(row["latitud"]),
        longitud=float(row["longitud"]),
        distancia_km=_optional_float(row.get("distancia_km")),
        comercio_id=int(row["comercio_id"]),
        comercio_marca=_optional_str(row.get("comercio_marca")),
        bandera_nombre=_optional_str(row.get("bandera_nombre")),
        bandera_logo_url=_optional_str(row.get("bandera_logo_url")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
