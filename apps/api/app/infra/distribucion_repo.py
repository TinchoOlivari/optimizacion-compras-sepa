from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from psycopg.rows import dict_row

from app.core.config import get_settings
from app.domain.optimizacion import (
    AsignacionSucursalResultado,
    ConfiguracionOptimizacion,
    DistribucionConfigError,
    IDistribucionRepository,
    IPreferenciasRepository,
    ItemAsignadoResultado,
    ItemCarritoOptimizacion,
    ItemNoAsignadoResultado,
    OfertaItemCandidata,
    ParadaResultado,
    PreferenciaOptimizacion,
    ResultadoDistribucion,
    RuteoResultado,
)
from app.infra.db import get_connection


class PreferenciasRepository(IPreferenciasRepository):
    def obtener_configuracion(self, usuario_id: int) -> ConfiguracionOptimizacion:
        settings = get_settings()
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        radio_km,
                        max_paradas,
                        modo_preferencia,
                        ubicacion_referencia_lat,
                        ubicacion_referencia_lon,
                        ubicacion_referencia_direccion,
                        ubicacion_referencia_modalidad
                    FROM preferencias_optimizacion
                    WHERE usuario_id = %s
                    """,
                    (usuario_id,),
                )
                row = cur.fetchone()

        por_defecto_aplicado: list[str] = []
        radio_km = None
        max_paradas = settings.default_max_paradas
        preferencia: PreferenciaOptimizacion = _normalizar_preferencia(settings.default_preferencia)
        lat = None
        lon = None
        direccion: str | None = None
        modalidad: str | None = None

        if row is not None:
            radio_raw = row["radio_km"]
            if radio_raw is not None:
                radio_km = _to_int(radio_raw)
            if row["max_paradas"] is not None:
                max_paradas = _to_int(row["max_paradas"])
            else:
                por_defecto_aplicado.append("max_paradas")

            if row["modo_preferencia"] is not None:
                preferencia = _normalizar_preferencia(str(row["modo_preferencia"]))
            else:
                por_defecto_aplicado.append("preferencia")

            lat = _to_float(row["ubicacion_referencia_lat"])
            lon = _to_float(row["ubicacion_referencia_lon"])
            if row["ubicacion_referencia_direccion"] is not None:
                direccion = str(row["ubicacion_referencia_direccion"])
            if row["ubicacion_referencia_modalidad"] is not None:
                modalidad = str(row["ubicacion_referencia_modalidad"])
        else:
            por_defecto_aplicado.extend(["max_paradas", "preferencia"])

        if radio_km is None:
            raise DistribucionConfigError("Debés configurar radio_km para distribuir.")
        if lat is None or lon is None:
            raise DistribucionConfigError(
                "Debés configurar ubicación de referencia para distribuir."
            )

        return ConfiguracionOptimizacion(
            radio_km=radio_km,
            max_paradas=max_paradas,
            preferencia=preferencia,
            origen_lat=lat,
            origen_lon=lon,
            por_defecto_aplicado=tuple(por_defecto_aplicado),
            origen_direccion=direccion,
            origen_modalidad=modalidad,
        )

    def guardar_configuracion(
        self,
        usuario_id: int,
        *,
        radio_km: int | None,
        max_paradas: int | None,
        preferencia: str | None,
        origen_lat: float | None,
        origen_lon: float | None,
        origen_direccion: str | None,
        origen_modalidad: str | None,
    ) -> ConfiguracionOptimizacion:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO preferencias_optimizacion (
                        usuario_id,
                        radio_km,
                        max_paradas,
                        modo_preferencia,
                        ubicacion_referencia_lat,
                        ubicacion_referencia_lon,
                        ubicacion_referencia_direccion,
                        ubicacion_referencia_modalidad,
                        ubicacion_referencia_geo
                    ) VALUES (
                        %s, %s, %s, %s::preferencia_optimizacion,
                        %s, %s, %s, %s::modalidad_ubicacion,
                        CASE WHEN %s IS NOT NULL AND %s IS NOT NULL
                            THEN ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                            ELSE NULL
                        END
                    )
                    ON CONFLICT (usuario_id)
                    DO UPDATE SET
                        radio_km = COALESCE(EXCLUDED.radio_km, preferencias_optimizacion.radio_km),
                        max_paradas = COALESCE(
                            EXCLUDED.max_paradas,
                            preferencias_optimizacion.max_paradas
                        ),
                        modo_preferencia = COALESCE(
                            EXCLUDED.modo_preferencia,
                            preferencias_optimizacion.modo_preferencia
                        ),
                        ubicacion_referencia_lat = COALESCE(
                            EXCLUDED.ubicacion_referencia_lat,
                            preferencias_optimizacion.ubicacion_referencia_lat
                        ),
                        ubicacion_referencia_lon = COALESCE(
                            EXCLUDED.ubicacion_referencia_lon,
                            preferencias_optimizacion.ubicacion_referencia_lon
                        ),
                        ubicacion_referencia_direccion = COALESCE(
                            EXCLUDED.ubicacion_referencia_direccion,
                            preferencias_optimizacion.ubicacion_referencia_direccion
                        ),
                        ubicacion_referencia_modalidad = COALESCE(
                            EXCLUDED.ubicacion_referencia_modalidad,
                            preferencias_optimizacion.ubicacion_referencia_modalidad
                        ),
                        ubicacion_referencia_geo = COALESCE(
                            EXCLUDED.ubicacion_referencia_geo,
                            preferencias_optimizacion.ubicacion_referencia_geo
                        )
                    """,
                    (
                        usuario_id,
                        radio_km,
                        max_paradas,
                        preferencia,
                        origen_lat,
                        origen_lon,
                        origen_direccion,
                        origen_modalidad,
                        origen_lat,
                        origen_lon,
                        origen_lon,
                        origen_lat,
                    ),
                )
                conn.commit()
        return self.obtener_configuracion(usuario_id)


class DistribucionRepository(IDistribucionRepository):
    def obtener_items_carrito(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> list[ItemCarritoOptimizacion]:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        ic.id AS item_carrito_id,
                        ic.producto_id,
                        p.nombre AS nombre_producto,
                        p.url_imagen,
                        ic.cantidad
                    FROM item_carrito ic
                    INNER JOIN carrito c ON c.id = ic.carrito_id
                    INNER JOIN producto p ON p.id = ic.producto_id
                    WHERE c.usuario_id = %s AND c.id = %s
                    ORDER BY ic.id
                    """,
                    (usuario_id, carrito_id),
                )
                rows = cur.fetchall()
        return [
            ItemCarritoOptimizacion(
                item_carrito_id=_to_int(row["item_carrito_id"]),
                producto_id=_to_int(row["producto_id"]),
                nombre_producto=str(row["nombre_producto"]),
                cantidad=_to_int(row["cantidad"]),
                url_imagen=str(row["url_imagen"]) if row["url_imagen"] is not None else None,
            )
            for row in rows
        ]

    def obtener_ofertas_candidatas(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        origen_lat: float,
        origen_lon: float,
        radio_km: int,
    ) -> list[OfertaItemCandidata]:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        ic.id AS item_carrito_id,
                        ic.producto_id,
                        pr.id AS precio_id,
                        s.id AS sucursal_id,
                        COALESCE(s.nombre, c.razon_social) AS sucursal,
                        c.razon_social AS comercio,
                        s.direccion,
                        s.localidad,
                        s.provincia,
                        s.latitud,
                        s.longitud,
                        ST_Distance(
                            s.geo,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        ) / 1000 AS distancia_km,
                        b.nombre AS bandera_nombre,
                        b.url_logo AS bandera_logo_url,
                        pr.valor AS precio_unitario
                    FROM item_carrito ic
                    INNER JOIN carrito ca ON ca.id = ic.carrito_id
                    INNER JOIN precio pr ON pr.producto_id = ic.producto_id
                    INNER JOIN sucursal s ON s.id = pr.sucursal_id
                    INNER JOIN comercio c ON c.id = s.comercio_id
                    LEFT JOIN bandera b ON b.id = s.bandera_id
                    WHERE ca.usuario_id = %s
                      AND ca.id = %s
                      AND s.geo IS NOT NULL
                      AND ST_DWithin(
                            s.geo,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                            %s * 1000
                      )
                      AND pr.fecha_vigencia = (
                            SELECT MAX(pr2.fecha_vigencia)
                            FROM precio pr2
                            WHERE pr2.producto_id = pr.producto_id
                              AND pr2.sucursal_id = pr.sucursal_id
                      )
                    ORDER BY ic.id, pr.valor ASC
                    """,
                    (
                        origen_lon,
                        origen_lat,
                        usuario_id,
                        carrito_id,
                        origen_lon,
                        origen_lat,
                        radio_km,
                    ),
                )
                rows = cur.fetchall()

        return [
            OfertaItemCandidata(
                item_carrito_id=_to_int(row["item_carrito_id"]),
                producto_id=_to_int(row["producto_id"]),
                precio_id=_to_int(row["precio_id"]),
                sucursal_id=_to_int(row["sucursal_id"]),
                sucursal=str(row["sucursal"]),
                comercio=str(row["comercio"]),
                direccion=str(row["direccion"]) if row["direccion"] is not None else None,
                localidad=str(row["localidad"]) if row["localidad"] is not None else None,
                provincia=str(row["provincia"]) if row["provincia"] is not None else None,
                latitud=_to_float(row["latitud"]) or 0.0,
                longitud=_to_float(row["longitud"]) or 0.0,
                distancia_km=_to_float(row["distancia_km"]),
                bandera_nombre=(
                    str(row["bandera_nombre"])
                    if row["bandera_nombre"] is not None
                    else None
                ),
                bandera_logo_url=str(row["bandera_logo_url"])
                if row["bandera_logo_url"] is not None
                else None,
                precio_unitario=_to_float(row["precio_unitario"]) or 0.0,
            )
            for row in rows
        ]

    def calcular_costo_referencia(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        origen_lat: float,
        origen_lon: float,
        radio_km: int,
    ) -> float | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    WITH items AS (
                        SELECT ic.id, ic.producto_id, ic.cantidad
                        FROM item_carrito ic
                        JOIN carrito c ON c.id = ic.carrito_id
                        WHERE c.usuario_id = %s AND c.id = %s
                    ),
                    candidatos AS (
                        SELECT s.id AS sucursal_id
                        FROM sucursal s
                        WHERE s.geo IS NOT NULL
                          AND ST_DWithin(
                                s.geo,
                                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                                %s * 1000
                          )
                    ),
                    cobertura AS (
                        SELECT
                            c.sucursal_id,
                            COUNT(DISTINCT i.producto_id) AS productos_cubiertos
                        FROM candidatos c
                        JOIN items i ON true
                        JOIN precio pr
                          ON pr.sucursal_id = c.sucursal_id
                         AND pr.producto_id = i.producto_id
                        GROUP BY c.sucursal_id
                    ),
                    mejor AS (
                        SELECT sucursal_id
                        FROM cobertura
                        ORDER BY productos_cubiertos DESC, sucursal_id ASC
                        LIMIT 1
                    )
                    SELECT SUM(i.cantidad * pr.valor) AS costo
                    FROM items i
                    JOIN mejor m ON true
                    JOIN precio pr
                      ON pr.sucursal_id = m.sucursal_id
                     AND pr.producto_id = i.producto_id
                    WHERE pr.fecha_vigencia = (
                        SELECT MAX(pr2.fecha_vigencia)
                        FROM precio pr2
                        WHERE pr2.producto_id = pr.producto_id
                          AND pr2.sucursal_id = pr.sucursal_id
                    )
                    """,
                    (usuario_id, carrito_id, origen_lon, origen_lat, radio_km),
                )
                row = cur.fetchone()

        if row is None or row["costo"] is None:
            return None
        return _to_float(row["costo"])

    def guardar_distribucion(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        configuracion: ConfiguracionOptimizacion,
        asignaciones: list[AsignacionSucursalResultado],
        items_no_asignados: list[ItemNoAsignadoResultado],
        ruteo: RuteoResultado,
        costo_total_estimado: float,
        ahorro_estimado: float | None,
    ) -> ResultadoDistribucion:
        fecha_calculo = datetime.now(UTC)
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT id FROM carrito WHERE id = %s AND usuario_id = %s",
                    (carrito_id, usuario_id),
                )
                if cur.fetchone() is None:
                    raise RuntimeError("Carrito no encontrado o sin permisos")

                cur.execute(
                    (
                        "UPDATE carrito_distribuido "
                        "SET vigente = false "
                        "WHERE carrito_id = %s AND vigente = true"
                    ),
                    (carrito_id,),
                )
                cur.execute(
                    """
                    INSERT INTO carrito_distribuido (
                        carrito_id,
                        fecha_calculo,
                        costo_total_estimado,
                        ahorro_estimado,
                        vigente,
                        cfg_radio_km,
                        cfg_max_paradas,
                        cfg_preferencia,
                        cfg_origen_lat,
                        cfg_origen_lon,
                        cfg_origen_geo
                    ) VALUES (
                        %s, %s, %s, %s, true,
                        %s, %s, %s::preferencia_optimizacion,
                        %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    )
                    RETURNING id
                    """,
                    (
                        carrito_id,
                        fecha_calculo,
                        costo_total_estimado,
                        ahorro_estimado,
                        configuracion.radio_km,
                        configuracion.max_paradas,
                        configuracion.preferencia,
                        configuracion.origen_lat,
                        configuracion.origen_lon,
                        configuracion.origen_lon,
                        configuracion.origen_lat,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No se pudo crear carrito_distribuido")
                distribucion_id = _to_int(row["id"])

                for asignacion in asignaciones:
                    cur.execute(
                        """
                        INSERT INTO asignacion_sucursal (
                            carrito_distribuido_id,
                            sucursal_id,
                            subtotal
                        )
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (distribucion_id, asignacion.sucursal_id, asignacion.subtotal),
                    )
                    asignacion_row = cur.fetchone()
                    if asignacion_row is None:
                        raise RuntimeError("No se pudo crear asignacion_sucursal")
                    asignacion_id = _to_int(asignacion_row["id"])

                    for item in asignacion.items:
                        cur.execute(
                            """
                            INSERT INTO item_asignado (
                                asignacion_sucursal_id,
                                item_carrito_id,
                                precio_id,
                                cantidad,
                                precio_unitario,
                                subtotal
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                asignacion_id,
                                item.item_carrito_id,
                                item.precio_id,
                                item.cantidad,
                                item.precio_unitario,
                                item.subtotal,
                            ),
                        )

                cur.execute(
                    (
                        "INSERT INTO ruteo (carrito_distribuido_id, distancia_total_km) "
                        "VALUES (%s, %s) RETURNING id"
                    ),
                    (distribucion_id, ruteo.distancia_total_km),
                )
                ruteo_row = cur.fetchone()
                if ruteo_row is None:
                    raise RuntimeError("No se pudo crear ruteo")
                ruteo_id = _to_int(ruteo_row["id"])

                for parada in ruteo.paradas:
                    origen_lat = configuracion.origen_lat if parada.es_origen else None
                    origen_lon = configuracion.origen_lon if parada.es_origen else None
                    cur.execute(
                        """
                        INSERT INTO parada (
                            ruteo_id,
                            sucursal_id,
                            orden,
                            distancia_desde_anterior_km,
                            es_origen,
                            es_adicional,
                            origen_lat,
                            origen_lon
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            ruteo_id,
                            parada.sucursal_id,
                            parada.orden,
                            parada.distancia_desde_anterior_km,
                            parada.es_origen,
                            parada.es_adicional,
                            origen_lat,
                            origen_lon,
                        ),
                    )

                for no_asignado in items_no_asignados:
                    cur.execute(
                        """
                        INSERT INTO item_no_asignado (
                            carrito_distribuido_id,
                            item_carrito_id,
                            producto_id,
                            nombre_producto,
                            cantidad
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            distribucion_id,
                            no_asignado.item_carrito_id,
                            no_asignado.producto_id,
                            no_asignado.nombre_producto,
                            no_asignado.cantidad,
                        ),
                    )

                conn.commit()

        return ResultadoDistribucion(
            fecha_calculo=fecha_calculo,
            costo_total_estimado=round(costo_total_estimado, 2),
            ahorro_estimado=round(ahorro_estimado, 2) if ahorro_estimado is not None else None,
            configuracion=configuracion,
            asignaciones=asignaciones,
            items_no_asignados=items_no_asignados,
            ruteo=ruteo,
            id=distribucion_id,
        )

    def obtener_distribucion_vigente(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> ResultadoDistribucion | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        cd.id,
                        cd.fecha_calculo,
                        cd.costo_total_estimado,
                        cd.ahorro_estimado,
                        cd.cfg_radio_km,
                        cd.cfg_max_paradas,
                        cd.cfg_preferencia,
                        cd.cfg_origen_lat,
                        cd.cfg_origen_lon
                    FROM carrito_distribuido cd
                    JOIN carrito c ON c.id = cd.carrito_id
                    WHERE c.usuario_id = %s AND c.id = %s AND cd.vigente = true
                    ORDER BY cd.fecha_calculo DESC
                    LIMIT 1
                    """,
                    (usuario_id, carrito_id),
                )
                head = cur.fetchone()
                if head is None:
                    return None
                distribucion_id = _to_int(head["id"])

                cur.execute(
                    """
                    SELECT
                        a.id AS asignacion_id,
                        a.sucursal_id,
                        a.subtotal,
                        COALESCE(s.nombre, c.razon_social) AS sucursal,
                        c.razon_social AS comercio,
                        s.direccion,
                        s.localidad,
                        s.provincia,
                        s.latitud,
                        s.longitud,
                        ST_Distance(s.geo, cd.cfg_origen_geo) / 1000 AS distancia_km,
                        b.nombre AS bandera_nombre,
                        b.url_logo AS bandera_logo_url,
                        ia.item_carrito_id,
                        ia.precio_id,
                        ia.cantidad,
                        ia.precio_unitario,
                        ia.subtotal AS item_subtotal,
                        p.id AS producto_id,
                        p.nombre AS producto_nombre,
                        p.url_imagen
                    FROM asignacion_sucursal a
                    JOIN carrito_distribuido cd ON cd.id = a.carrito_distribuido_id
                    JOIN sucursal s ON s.id = a.sucursal_id
                    JOIN comercio c ON c.id = s.comercio_id
                    LEFT JOIN bandera b ON b.id = s.bandera_id
                    LEFT JOIN item_asignado ia ON ia.asignacion_sucursal_id = a.id
                    LEFT JOIN item_carrito ic ON ic.id = ia.item_carrito_id
                    LEFT JOIN producto p ON p.id = ic.producto_id
                    WHERE a.carrito_distribuido_id = %s
                    ORDER BY a.id, ia.id
                    """,
                    (distribucion_id,),
                )
                asignaciones_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT
                        pa.orden,
                        pa.sucursal_id,
                        pa.es_origen,
                        pa.es_adicional,
                        pa.distancia_desde_anterior_km,
                        COALESCE(s.nombre, 'Origen') AS nombre
                    FROM ruteo r
                    JOIN parada pa ON pa.ruteo_id = r.id
                    LEFT JOIN sucursal s ON s.id = pa.sucursal_id
                    WHERE r.carrito_distribuido_id = %s
                    ORDER BY pa.orden
                    """,
                    (distribucion_id,),
                )
                paradas_rows = cur.fetchall()

                cur.execute(
                    "SELECT distancia_total_km FROM ruteo WHERE carrito_distribuido_id = %s",
                    (distribucion_id,),
                )
                ruteo_row = cur.fetchone()

                cur.execute(
                    """
                    SELECT item_carrito_id, producto_id, nombre_producto, cantidad
                    FROM item_no_asignado
                    WHERE carrito_distribuido_id = %s
                    ORDER BY item_carrito_id
                    """,
                    (distribucion_id,),
                )
                no_asignados_rows = cur.fetchall()

        asignaciones_map: dict[int, AsignacionSucursalResultado] = {}
        for row in asignaciones_rows:
            asignacion_id = _to_int(row["asignacion_id"])
            asignacion = asignaciones_map.get(asignacion_id)
            if asignacion is None:
                asignacion = AsignacionSucursalResultado(
                    sucursal_id=_to_int(row["sucursal_id"]),
                    sucursal=str(row["sucursal"]),
                    comercio=str(row["comercio"]),
                    direccion=str(row["direccion"]) if row["direccion"] is not None else None,
                    localidad=str(row["localidad"]) if row["localidad"] is not None else None,
                    provincia=str(row["provincia"]) if row["provincia"] is not None else None,
                    latitud=_to_float(row["latitud"]) or 0.0,
                    longitud=_to_float(row["longitud"]) or 0.0,
                    distancia_km=_to_float(row["distancia_km"]),
                    bandera_nombre=str(row["bandera_nombre"])
                    if row["bandera_nombre"] is not None
                    else None,
                    bandera_logo_url=str(row["bandera_logo_url"])
                    if row["bandera_logo_url"] is not None
                    else None,
                    subtotal=_to_float(row["subtotal"]) or 0.0,
                    items=[],
                )
                asignaciones_map[asignacion_id] = asignacion

            if row["item_carrito_id"] is not None:
                asignacion.items.append(
                    ItemAsignadoResultado(
                        item_carrito_id=_to_int(row["item_carrito_id"]),
                        producto_id=_to_int(row["producto_id"]),
                        nombre_producto=str(row["producto_nombre"]),
                        cantidad=_to_int(row["cantidad"]),
                        precio_id=_to_int(row["precio_id"]),
                        precio_unitario=_to_float(row["precio_unitario"]) or 0.0,
                        subtotal=_to_float(row["item_subtotal"]) or 0.0,
                        url_imagen=str(row["url_imagen"])
                        if row["url_imagen"] is not None
                        else None,
                    )
                )

        orden_por_sucursal = {
            _to_int(row["sucursal_id"]): _to_int(row["orden"])
            for row in paradas_rows
            if row["sucursal_id"] is not None
        }
        asignacion_por_sucursal = {
            asignacion.sucursal_id: asignacion for asignacion in asignaciones_map.values()
        }

        asignaciones_ordenadas = sorted(
            asignaciones_map.values(),
            key=lambda asignacion: (
                orden_por_sucursal.get(asignacion.sucursal_id, len(orden_por_sucursal)),
                asignacion.sucursal_id,
            ),
        )

        paradas: list[ParadaResultado] = []
        for row in paradas_rows:
            sucursal_id = _to_int(row["sucursal_id"]) if row["sucursal_id"] is not None else None
            productos = []
            if sucursal_id is not None and sucursal_id in asignacion_por_sucursal:
                productos = [item.nombre_producto for item in asignacion_por_sucursal[sucursal_id].items]

            paradas.append(
                ParadaResultado(
                    orden=_to_int(row["orden"]),
                    sucursal_id=sucursal_id,
                    nombre=str(row["nombre"]),
                    es_origen=bool(row["es_origen"]),
                    es_adicional=bool(row["es_adicional"]),
                    distancia_desde_anterior_km=_to_float(row["distancia_desde_anterior_km"]) or 0.0,
                    productos=productos,
                )
            )

        return ResultadoDistribucion(
            fecha_calculo=_to_datetime(head["fecha_calculo"]),
            costo_total_estimado=_to_float(head["costo_total_estimado"]) or 0.0,
            ahorro_estimado=_to_float(head["ahorro_estimado"])
            if head["ahorro_estimado"] is not None
            else None,
            configuracion=ConfiguracionOptimizacion(
                radio_km=_to_int(head["cfg_radio_km"]),
                max_paradas=_to_int(head["cfg_max_paradas"]),
                preferencia=_normalizar_preferencia(str(head["cfg_preferencia"])),
                origen_lat=_to_float(head["cfg_origen_lat"]) or 0.0,
                origen_lon=_to_float(head["cfg_origen_lon"]) or 0.0,
                por_defecto_aplicado=(),
            ),
            asignaciones=asignaciones_ordenadas,
            items_no_asignados=[
                ItemNoAsignadoResultado(
                    item_carrito_id=_to_int(row["item_carrito_id"]),
                    producto_id=_to_int(row["producto_id"]),
                    nombre_producto=str(row["nombre_producto"]),
                    cantidad=_to_int(row["cantidad"]),
                )
                for row in no_asignados_rows
            ],
            ruteo=RuteoResultado(
                distancia_total_km=(
                    (_to_float(ruteo_row["distancia_total_km"]) or 0.0) if ruteo_row else 0.0
                ),
                paradas=paradas,
            ),
            id=distribucion_id,
        )


def _to_int(value: Any) -> int:
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)


def _normalizar_preferencia(value: str) -> PreferenciaOptimizacion:
    normalized = value.strip().upper()
    if normalized not in {"MENOR_PRECIO", "MENOR_DESPLAZAMIENTO", "BALANCEADO"}:
        raise DistribucionConfigError("Preferencia de optimización inválida.")
    return cast(PreferenciaOptimizacion, normalized)
