from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal

import psycopg

from ingesta.parser import ComercioCSV, ProductoCSV, SucursalCSV

_SEPA_ID_MAX_LENGTH = 20
_PROVINCIA_MAX_LENGTH = 64


class RepositorioSEPA:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def upsert_comercios(self, rows: list[ComercioCSV]) -> dict[str, int]:
        if not rows:
            return {}

        deduplicados: dict[str, str] = {}
        for row in rows:
            deduplicados[row.cuit] = row.razon_social

        ids_por_cuit: dict[str, int] = {}
        with self.connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tmp_comercio")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_comercio (
                    cuit VARCHAR(11) NOT NULL,
                    razon_social VARCHAR(255) NOT NULL
                ) ON COMMIT DROP
                """
            )
            with cur.copy("COPY tmp_comercio (cuit, razon_social) FROM STDIN") as copy:
                for cuit, razon_social in deduplicados.items():
                    copy.write_row((cuit, razon_social))

            cur.execute(
                """
                INSERT INTO comercio (cuit, razon_social)
                SELECT cuit, razon_social
                FROM tmp_comercio
                ON CONFLICT (cuit)
                DO UPDATE
                SET razon_social = EXCLUDED.razon_social
                WHERE comercio.razon_social IS DISTINCT FROM EXCLUDED.razon_social
                """
            )

            cur.execute(
                """
                SELECT c.cuit, c.id
                FROM comercio c
                JOIN (SELECT DISTINCT cuit FROM tmp_comercio) t USING (cuit)
                """
            )
            for cuit, comercio_id in cur.fetchall():
                ids_por_cuit[str(cuit)] = int(comercio_id)
        return ids_por_cuit

    def upsert_banderas(self, rows: list[ComercioCSV]) -> dict[str, int]:
        if not rows:
            return {}

        deduplicados: dict[str, str] = {}
        for row in rows:
            deduplicados[row.id_bandera] = row.bandera_nombre

        ids_por_id_bandera: dict[str, int] = {}
        with self.connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tmp_bandera")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_bandera (
                    sepa_id_bandera VARCHAR(20) NOT NULL,
                    nombre VARCHAR(255) NOT NULL
                ) ON COMMIT DROP
                """
            )
            with cur.copy(
                "COPY tmp_bandera (sepa_id_bandera, nombre) FROM STDIN"
            ) as copy:
                for id_bandera, nombre in deduplicados.items():
                    copy.write_row((id_bandera, nombre))

            cur.execute(
                """
                INSERT INTO bandera (nombre)
                SELECT DISTINCT nombre
                FROM tmp_bandera
                ON CONFLICT (nombre) DO NOTHING
                """
            )

            cur.execute(
                """
                SELECT tb.sepa_id_bandera, b.id
                FROM tmp_bandera tb
                JOIN bandera b ON b.nombre = tb.nombre
                """
            )
            for id_bandera, bandera_id in cur.fetchall():
                ids_por_id_bandera[str(id_bandera)] = int(bandera_id)
        return ids_por_id_bandera

    def upsert_sucursales(
        self,
        rows: list[SucursalCSV],
        comercio_ids_por_id_comercio: Mapping[str, int],
        bandera_ids_por_id_bandera: Mapping[str, int],
    ) -> dict[tuple[str, str, str], int]:
        if not rows:
            return {}

        payload: dict[tuple[str, str, str], tuple[int, int, str | None, str | None, str | None, str | None, float | None, float | None]] = {}
        for row in rows:
            comercio_id = comercio_ids_por_id_comercio.get(row.id_comercio)
            bandera_id = bandera_ids_por_id_bandera.get(row.id_bandera)
            if comercio_id is None or bandera_id is None:
                continue
            key = (row.id_comercio, row.id_bandera, row.id_sucursal)
            payload[key] = (
                comercio_id,
                bandera_id,
                row.nombre or None,
                row.direccion or None,
                row.localidad or None,
                row.provincia or None,
                row.latitud,
                row.longitud,
            )

        if not payload:
            return {}

        ids_sucursal: dict[tuple[str, str, str], int] = {}
        with self.connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tmp_sucursal")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_sucursal (
                    comercio_id BIGINT NOT NULL,
                    bandera_id BIGINT NOT NULL,
                    sepa_id_comercio VARCHAR(20) NOT NULL,
                    sepa_id_bandera VARCHAR(20) NOT NULL,
                    sepa_id_sucursal VARCHAR(20) NOT NULL,
                    nombre VARCHAR(255) NULL,
                    direccion VARCHAR(255) NULL,
                    localidad VARCHAR(120) NULL,
                    provincia VARCHAR(64) NULL,
                    latitud DOUBLE PRECISION NULL,
                    longitud DOUBLE PRECISION NULL
                ) ON COMMIT DROP
                """
            )
            with cur.copy(
                """
                COPY tmp_sucursal (
                    comercio_id,
                    bandera_id,
                    sepa_id_comercio,
                    sepa_id_bandera,
                    sepa_id_sucursal,
                    nombre,
                    direccion,
                    localidad,
                    provincia,
                    latitud,
                    longitud
                ) FROM STDIN
                """
            ) as copy:
                for (id_comercio, id_bandera, id_sucursal), (
                    comercio_id,
                    bandera_id,
                    nombre,
                    direccion,
                    localidad,
                    provincia,
                    latitud,
                    longitud,
                ) in payload.items():
                    _validate_sucursal_copy_row(id_comercio, id_bandera, id_sucursal, provincia)
                    copy.write_row(
                        (
                            comercio_id,
                            bandera_id,
                            id_comercio,
                            id_bandera,
                            id_sucursal,
                            nombre,
                            direccion,
                            localidad,
                            provincia,
                            latitud,
                            longitud,
                        )
                    )

            cur.execute(
                """
                INSERT INTO sucursal (
                    comercio_id,
                    bandera_id,
                    sepa_id_comercio,
                    sepa_id_bandera,
                    sepa_id_sucursal,
                    nombre,
                    direccion,
                    localidad,
                    provincia,
                    latitud,
                    longitud,
                    geo
                )
                SELECT
                    comercio_id,
                    bandera_id,
                    sepa_id_comercio,
                    sepa_id_bandera,
                    sepa_id_sucursal,
                    nombre,
                    direccion,
                    localidad,
                    provincia,
                    latitud,
                    longitud,
                    CASE
                        WHEN longitud IS NOT NULL AND latitud IS NOT NULL
                        THEN ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography
                        ELSE NULL
                    END AS geo
                FROM tmp_sucursal
                ON CONFLICT (sepa_id_comercio, sepa_id_bandera, sepa_id_sucursal)
                DO UPDATE
                SET
                    comercio_id = EXCLUDED.comercio_id,
                    bandera_id = EXCLUDED.bandera_id,
                    nombre = EXCLUDED.nombre,
                    direccion = EXCLUDED.direccion,
                    localidad = EXCLUDED.localidad,
                    provincia = EXCLUDED.provincia,
                    latitud = EXCLUDED.latitud,
                    longitud = EXCLUDED.longitud,
                    geo = EXCLUDED.geo
                WHERE sucursal.comercio_id IS DISTINCT FROM EXCLUDED.comercio_id
                   OR sucursal.bandera_id IS DISTINCT FROM EXCLUDED.bandera_id
                   OR sucursal.nombre IS DISTINCT FROM EXCLUDED.nombre
                   OR sucursal.direccion IS DISTINCT FROM EXCLUDED.direccion
                   OR sucursal.localidad IS DISTINCT FROM EXCLUDED.localidad
                   OR sucursal.provincia IS DISTINCT FROM EXCLUDED.provincia
                   OR sucursal.latitud IS DISTINCT FROM EXCLUDED.latitud
                   OR sucursal.longitud IS DISTINCT FROM EXCLUDED.longitud
                   OR sucursal.geo IS DISTINCT FROM EXCLUDED.geo
                """
            )

            cur.execute(
                """
                SELECT s.sepa_id_comercio, s.sepa_id_bandera, s.sepa_id_sucursal, s.id
                FROM sucursal s
                JOIN (
                    SELECT DISTINCT sepa_id_comercio, sepa_id_bandera, sepa_id_sucursal
                    FROM tmp_sucursal
                ) t
                    ON s.sepa_id_comercio = t.sepa_id_comercio
                    AND s.sepa_id_bandera = t.sepa_id_bandera
                    AND s.sepa_id_sucursal = t.sepa_id_sucursal
                """
            )
            for id_comercio, id_bandera, id_sucursal, sucursal_id in cur.fetchall():
                ids_sucursal[(str(id_comercio), str(id_bandera), str(id_sucursal))] = int(sucursal_id)

        return ids_sucursal

    def upsert_productos(self, rows: list[ProductoCSV]) -> dict[str, int]:
        if not rows:
            return {}

        deduplicados: dict[str, tuple[str, str | None, str | None]] = {}
        for row in sorted(rows, key=lambda r: (r.id_comercio, r.id_bandera, r.id_sucursal)):
            if row.codigo_ean in deduplicados:
                continue
            presentacion = _build_presentacion(
                row.cantidad_presentacion,
                row.unidad_medida_presentacion,
            )
            deduplicados[row.codigo_ean] = (row.descripcion, row.marca or None, presentacion)

        ids_producto: dict[str, int] = {}
        with self.connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tmp_producto")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_producto (
                    codigo_ean VARCHAR(14) NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    marca VARCHAR(255) NULL,
                    presentacion VARCHAR(255) NULL
                ) ON COMMIT DROP
                """
            )
            with cur.copy("COPY tmp_producto (codigo_ean, nombre, marca, presentacion) FROM STDIN") as copy:
                for codigo_ean, (nombre, marca, presentacion) in deduplicados.items():
                    copy.write_row((codigo_ean, nombre, marca, presentacion))

            cur.execute(
                """
                INSERT INTO producto (codigo_ean, nombre, marca, presentacion)
                SELECT codigo_ean, nombre, marca, presentacion
                FROM tmp_producto
                ON CONFLICT (codigo_ean)
                DO NOTHING
                """
            )

            cur.execute(
                """
                SELECT p.codigo_ean, p.id
                FROM producto p
                JOIN (SELECT DISTINCT codigo_ean FROM tmp_producto) t USING (codigo_ean)
                """
            )
            for codigo_ean, producto_id in cur.fetchall():
                ids_producto[str(codigo_ean)] = int(producto_id)
        return ids_producto

    def upsert_precios(
        self,
        rows: list[ProductoCSV],
        producto_ids: Mapping[str, int],
        sucursal_ids: Mapping[tuple[str, str, str], int],
        fecha_vigencia: date,
    ) -> tuple[int, int, int]:
        if not rows:
            return (0, 0, 0)

        deduplicados: dict[tuple[int, int, date], Decimal] = {}
        huerfanas_producto = 0
        huerfanas_sucursal = 0
        for row in rows:
            if row.precio_lista <= 0:
                continue
            producto_id = producto_ids.get(row.codigo_ean)
            sucursal_id = sucursal_ids.get((row.id_comercio, row.id_bandera, row.id_sucursal))
            if producto_id is None:
                huerfanas_producto += 1
                continue
            if sucursal_id is None:
                huerfanas_sucursal += 1
                continue
            deduplicados[(producto_id, sucursal_id, fecha_vigencia)] = row.precio_lista

        if not deduplicados:
            return (0, huerfanas_producto, huerfanas_sucursal)

        with self.connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tmp_precio")
            cur.execute(
                """
                CREATE TEMP TABLE tmp_precio (
                    producto_id BIGINT NOT NULL,
                    sucursal_id BIGINT NOT NULL,
                    valor NUMERIC(12, 2) NOT NULL,
                    fecha_vigencia DATE NOT NULL
                ) ON COMMIT DROP
                """
            )
            with cur.copy("COPY tmp_precio (producto_id, sucursal_id, valor, fecha_vigencia) FROM STDIN") as copy:
                for (producto_id, sucursal_id, fecha), valor in deduplicados.items():
                    copy.write_row((producto_id, sucursal_id, valor, fecha))

            cur.execute(
                """
                INSERT INTO precio (producto_id, sucursal_id, valor, fecha_vigencia)
                SELECT producto_id, sucursal_id, valor, fecha_vigencia
                FROM tmp_precio
                ON CONFLICT (producto_id, sucursal_id)
                DO UPDATE SET
                    valor = EXCLUDED.valor,
                    fecha_vigencia = EXCLUDED.fecha_vigencia
                WHERE precio.valor IS DISTINCT FROM EXCLUDED.valor
                """
            )
            return (int(cur.rowcount), huerfanas_producto, huerfanas_sucursal)

    def delete_precios_por_sucursales(self, sucursal_ids: list[int]) -> int:
        if not sucursal_ids:
            return 0
        with self.connection.cursor() as cur:
            cur.execute(
                "DELETE FROM progreso_item"
                " WHERE item_asignado_id IN ("
                "  SELECT ia.id FROM item_asignado ia"
                "  JOIN precio p ON p.id = ia.precio_id"
                "  WHERE p.sucursal_id = ANY(%s)"
                " )",
                (sucursal_ids,),
            )
            cur.execute(
                "DELETE FROM item_asignado"
                " WHERE precio_id IN ("
                "  SELECT p.id FROM precio p"
                "  WHERE p.sucursal_id = ANY(%s)"
                " )",
                (sucursal_ids,),
            )
            cur.execute(
                "DELETE FROM precio WHERE sucursal_id = ANY(%s)",
                (sucursal_ids,),
            )
            return int(cur.rowcount)


def _build_presentacion(cantidad: str, unidad: str) -> str | None:
    merged = " ".join([cantidad.strip(), unidad.strip()]).strip()
    return merged or None


def _validate_sucursal_copy_row(
    id_comercio: str,
    id_bandera: str,
    id_sucursal: str,
    provincia: str | None,
) -> None:
    ids = {
        "id_comercio": id_comercio,
        "id_bandera": id_bandera,
        "id_sucursal": id_sucursal,
    }
    for field, value in ids.items():
        if len(value) > _SEPA_ID_MAX_LENGTH:
            raise ValueError(
                "Fila sucursal inválida para COPY: "
                f"{field} excede {_SEPA_ID_MAX_LENGTH} caracteres "
                f"(id_comercio={id_comercio}, id_bandera={id_bandera}, id_sucursal={id_sucursal})"
            )

    if provincia is not None and len(provincia) > _PROVINCIA_MAX_LENGTH:
        raise ValueError(
            "Fila sucursal inválida para COPY: "
            f"provincia excede {_PROVINCIA_MAX_LENGTH} caracteres "
            f"(id_comercio={id_comercio}, id_bandera={id_bandera}, id_sucursal={id_sucursal})"
        )
