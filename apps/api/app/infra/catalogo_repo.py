from datetime import UTC, datetime
from typing import Any

from psycopg.rows import dict_row

from app.domain.ports import ICatalogoRepository, PrecioProducto, ProductoResumen
from app.infra.db import get_connection


class CatalogoRepository(ICatalogoRepository):
    def buscar_por_ean(self, codigo_ean: str) -> ProductoResumen | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, codigo_ean, nombre, marca, presentacion, url_imagen
                    FROM producto
                    WHERE codigo_ean = %s
                    """,
                    (codigo_ean,),
                )
                row = cur.fetchone()
                return _map_producto(row)

    def buscar_por_nombre(self, texto: str, limite: int) -> list[ProductoResumen]:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, codigo_ean, nombre, marca, presentacion, url_imagen
                    FROM producto
                    WHERE nombre ILIKE '%%' || %s || '%%'
                       OR nombre %% %s
                    ORDER BY
                        CASE WHEN nombre ILIKE '%%' || %s || '%%' THEN 0 ELSE 1 END,
                        similarity(nombre, %s) DESC,
                        nombre ASC
                    LIMIT %s
                    """,
                    (texto, texto, texto, texto, limite),
                )
                rows = cur.fetchall()
                return [producto for row in rows if (producto := _map_producto(row)) is not None]

    def obtener_producto(self, producto_id: int) -> ProductoResumen | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, codigo_ean, nombre, marca, presentacion, url_imagen
                    FROM producto
                    WHERE id = %s
                    """,
                    (producto_id,),
                )
                row = cur.fetchone()
                return _map_producto(row)

    def obtener_precios_producto(
        self,
        producto_id: int,
        *,
        lat: float | None,
        lon: float | None,
        radio_km: int | None,
        limite: int | None = None,
    ) -> list[PrecioProducto]:
        if lat is None or lon is None or radio_km is None:
            return []

        limit_clause = "LIMIT %s" if limite is not None else ""
        params: tuple[Any, ...] = (
            producto_id,
            lon,
            lat,
            lon,
            lat,
            radio_km,
        )
        if limite is not None:
            params = (*params, limite)

        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    WITH precios_ultimos AS (
                        SELECT DISTINCT ON (p.sucursal_id)
                            p.sucursal_id,
                            p.valor,
                            p.fecha_vigencia
                        FROM precio p
                        WHERE p.producto_id = %s
                        ORDER BY p.sucursal_id, p.fecha_vigencia DESC
                    ),
                    candidatos AS (
                        SELECT
                            c.id AS comercio_id,
                            b.nombre AS comercio,
                            s.id AS sucursal_id,
                            COALESCE(s.nombre, c.razon_social) AS sucursal,
                            s.direccion,
                            s.localidad,
                            s.provincia,
                            pu.valor,
                            pu.fecha_vigencia,
                            ST_Distance(
                                s.geo,
                                ST_SetSRID(
                                    ST_MakePoint(
                                        %s::double precision,
                                        %s::double precision
                                    ),
                                    4326
                                )::geography
                            ) / 1000 AS distancia_km
                        FROM precios_ultimos pu
                        INNER JOIN sucursal s ON s.id = pu.sucursal_id
                        INNER JOIN comercio c ON c.id = s.comercio_id
                        INNER JOIN bandera b ON b.id = s.bandera_id
                        WHERE
                            s.geo IS NOT NULL
                            AND ST_DWithin(
                                s.geo,
                                ST_SetSRID(
                                    ST_MakePoint(
                                        %s::double precision,
                                        %s::double precision
                                    ),
                                    4326
                                )::geography,
                                %s::integer * 1000
                            )
                    ),
                    agregado AS (
                        SELECT
                            comercio_id,
                            comercio,
                            MIN(valor) AS valor,
                            MIN(distancia_km) AS distancia_km
                        FROM candidatos
                        GROUP BY comercio_id, comercio
                    ),
                    representante AS (
                        SELECT DISTINCT ON (a.comercio_id)
                            a.comercio_id,
                            a.comercio,
                            c.sucursal_id,
                            c.sucursal,
                            c.direccion,
                            c.localidad,
                            c.provincia,
                            a.valor,
                            c.fecha_vigencia,
                            a.distancia_km
                        FROM agregado a
                        INNER JOIN candidatos c ON c.comercio_id = a.comercio_id
                        ORDER BY
                            a.comercio_id,
                            CASE WHEN c.valor = a.valor THEN 0 ELSE 1 END,
                            c.distancia_km ASC,
                            c.sucursal_id ASC
                    )
                    SELECT
                        comercio_id,
                        comercio,
                        sucursal_id,
                        sucursal,
                        direccion,
                        localidad,
                        provincia,
                        valor,
                        fecha_vigencia,
                        distancia_km
                    FROM representante
                    ORDER BY distancia_km ASC, comercio ASC
                    {limit_clause}
                    """,
                    params,
                )
                rows = cur.fetchall()
                return [_map_precio(row) for row in rows]


def _map_producto(row: dict[str, Any] | None) -> ProductoResumen | None:
    if row is None:
        return None
    return ProductoResumen(
        id=int(row["id"]),
        codigo_ean=str(row["codigo_ean"]),
        nombre=str(row["nombre"]),
        marca=_optional_str(row.get("marca")),
        presentacion=_optional_str(row.get("presentacion")),
        url_imagen=_optional_str(row.get("url_imagen")),
    )


def _map_precio(row: dict[str, Any]) -> PrecioProducto:
    fecha_raw = row["fecha_vigencia"]
    if isinstance(fecha_raw, datetime):
        fecha_vigencia = fecha_raw
    else:
        fecha_vigencia = datetime.fromisoformat(str(fecha_raw)).replace(tzinfo=UTC)

    return PrecioProducto(
        comercio_id=int(row["comercio_id"]),
        comercio=str(row["comercio"]),
        sucursal_id=int(row["sucursal_id"]),
        sucursal=str(row["sucursal"]),
        direccion=_optional_str(row.get("direccion")),
        localidad=_optional_str(row.get("localidad")),
        provincia=_optional_str(row.get("provincia")),
        precio=float(row["valor"]),
        fecha_vigencia=fecha_vigencia,
        distancia_km=_optional_float(row.get("distancia_km")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
