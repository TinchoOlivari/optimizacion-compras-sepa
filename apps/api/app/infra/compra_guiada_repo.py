from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from psycopg.rows import dict_row

from app.domain.compra_guiada import (
    AlternativaFaltante,
    CompraGuiadaDetalle,
    CompraGuiadaNotFoundError,
    ConfianzaAlternativa,
    EstadoCierre,
    EstadoItem,
    EstadoItemActualizable,
    ICompraGuiadaRepository,
    ItemCompraGuiada,
    ParadaCompraGuiada,
    TipoAlternativaFaltante,
)
from app.infra.db import get_connection


class CompraGuiadaRepository(ICompraGuiadaRepository):
    def iniciar(self, usuario_id: int, carrito_distribuido_id: int) -> CompraGuiadaDetalle:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT cg.id
                    FROM compra_guiada cg
                    JOIN carrito_distribuido cd ON cd.id = cg.carrito_distribuido_id
                    JOIN carrito c ON c.id = cd.carrito_id
                    WHERE c.usuario_id = %s
                      AND cd.id = %s
                      AND cg.fecha_cierre IS NULL
                    LIMIT 1
                    """,
                    (usuario_id, carrito_distribuido_id),
                )
                activa = cur.fetchone()
                if activa is not None:
                    compra_id = _to_int(activa["id"])
                    conn.commit()
                    compra = self.obtener(usuario_id, compra_id)
                    if compra is None:
                        raise RuntimeError("Compra guiada activa no encontrada")
                    return compra

                cur.execute(
                    """
                    SELECT cd.id
                    FROM carrito_distribuido cd
                    JOIN carrito c ON c.id = cd.carrito_id
                    WHERE c.usuario_id = %s AND cd.id = %s
                    """,
                    (usuario_id, carrito_distribuido_id),
                )
                if cur.fetchone() is None:
                    raise CompraGuiadaNotFoundError("Distribución no encontrada o sin permisos.")

                cur.execute(
                    """
                    INSERT INTO compra_guiada (carrito_distribuido_id)
                    VALUES (%s)
                    RETURNING id
                    """,
                    (carrito_distribuido_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No se pudo crear compra_guiada")
                compra_id = _to_int(row["id"])

                cur.execute(
                    """
                    INSERT INTO progreso_item (
                        compra_guiada_id,
                        item_asignado_id,
                        estado,
                        sucursal_actual_id
                    )
                    SELECT %s, ia.id, 'PENDIENTE'::estado_item, a.sucursal_id
                    FROM item_asignado ia
                    JOIN asignacion_sucursal a ON a.id = ia.asignacion_sucursal_id
                    WHERE a.carrito_distribuido_id = %s
                    ORDER BY a.id, ia.id
                    """,
                    (compra_id, carrito_distribuido_id),
                )
                conn.commit()

        compra = self.obtener(usuario_id, compra_id)
        if compra is None:
            raise RuntimeError("No se pudo obtener la compra guiada creada")
        return compra

    def obtener(self, usuario_id: int, compra_id: int) -> CompraGuiadaDetalle | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        cg.id,
                        cg.carrito_distribuido_id,
                        cg.fecha_inicio,
                        cg.fecha_cierre,
                        cg.estado_cierre
                    FROM compra_guiada cg
                    JOIN carrito_distribuido cd ON cd.id = cg.carrito_distribuido_id
                    JOIN carrito c ON c.id = cd.carrito_id
                    WHERE c.usuario_id = %s AND cg.id = %s
                    """,
                    (usuario_id, compra_id),
                )
                head = cur.fetchone()
                if head is None:
                    return None

                cur.execute(
                    """
                    SELECT
                        pi.id AS progreso_item_id,
                        pi.estado,
                        ia.id AS item_asignado_id,
                        ia.item_carrito_id,
                        ia.cantidad,
                        ia.precio_unitario,
                        ia.subtotal AS item_subtotal,
                        p.id AS producto_id,
                        p.nombre AS producto_nombre,
                        p.url_imagen,
                        a.sucursal_id,
                        a.subtotal AS parada_subtotal,
                        COALESCE(s.nombre, co.razon_social) AS sucursal,
                        co.razon_social AS comercio,
                        s.direccion,
                        s.localidad,
                        s.provincia,
                        b.nombre AS bandera_nombre,
                        b.url_logo AS bandera_logo_url,
                        COALESCE(pa.orden, 999999) AS orden,
                        COALESCE(pa.distancia_desde_anterior_km, 0) AS distancia_desde_anterior_km,
                        COALESCE(pa.es_adicional, false) AS es_adicional
                    FROM progreso_item pi
                    JOIN item_asignado ia ON ia.id = pi.item_asignado_id
                    JOIN item_carrito ic ON ic.id = ia.item_carrito_id
                    JOIN producto p ON p.id = ic.producto_id
                    JOIN asignacion_sucursal a ON a.id = ia.asignacion_sucursal_id
                    JOIN sucursal s ON s.id = a.sucursal_id
                    JOIN comercio co ON co.id = s.comercio_id
                    LEFT JOIN bandera b ON b.id = s.bandera_id
                    LEFT JOIN ruteo r ON r.carrito_distribuido_id = a.carrito_distribuido_id
                    LEFT JOIN parada pa ON pa.ruteo_id = r.id AND pa.sucursal_id = a.sucursal_id
                    WHERE pi.compra_guiada_id = %s
                    ORDER BY orden, a.id, ia.id
                    """,
                    (compra_id,),
                )
                rows = cur.fetchall()

        paradas: dict[int, ParadaCompraGuiada] = {}
        for row in rows:
            sucursal_id = _to_int(row["sucursal_id"])
            parada = paradas.get(sucursal_id)
            if parada is None:
                parada = ParadaCompraGuiada(
                    orden=_to_int(row["orden"]),
                    sucursal_id=sucursal_id,
                    sucursal=str(row["sucursal"]),
                    comercio=str(row["comercio"]),
                    direccion=str(row["direccion"]) if row["direccion"] is not None else None,
                    localidad=str(row["localidad"]) if row["localidad"] is not None else None,
                    provincia=str(row["provincia"]) if row["provincia"] is not None else None,
                    distancia_desde_anterior_km=(
                        _to_float(row["distancia_desde_anterior_km"]) or 0.0
                    ),
                    bandera_nombre=str(row["bandera_nombre"])
                    if row["bandera_nombre"] is not None
                    else None,
                    bandera_logo_url=str(row["bandera_logo_url"])
                    if row["bandera_logo_url"] is not None
                    else None,
                    subtotal=_to_float(row["parada_subtotal"]) or 0.0,
                    es_adicional=bool(row["es_adicional"]),
                    items=[],
                )
                paradas[sucursal_id] = parada

            parada.items.append(
                ItemCompraGuiada(
                    progreso_item_id=_to_int(row["progreso_item_id"]),
                    item_asignado_id=_to_int(row["item_asignado_id"]),
                    item_carrito_id=_to_int(row["item_carrito_id"]),
                    producto_id=_to_int(row["producto_id"]),
                    nombre_producto=str(row["producto_nombre"]),
                    cantidad=_to_int(row["cantidad"]),
                    precio_unitario=_to_float(row["precio_unitario"]) or 0.0,
                    subtotal=_to_float(row["item_subtotal"]) or 0.0,
                    url_imagen=str(row["url_imagen"]) if row["url_imagen"] is not None else None,
                    estado=_normalizar_estado_item(str(row["estado"])),
                )
            )

        return CompraGuiadaDetalle(
            id=_to_int(head["id"]),
            carrito_distribuido_id=_to_int(head["carrito_distribuido_id"]),
            fecha_inicio=_to_datetime(head["fecha_inicio"]),
            fecha_cierre=_to_datetime(head["fecha_cierre"])
            if head["fecha_cierre"] is not None
            else None,
            estado_cierre=_normalizar_estado_cierre(str(head["estado_cierre"]))
            if head["estado_cierre"] is not None
            else None,
            paradas=list(paradas.values()),
        )

    def actualizar_item(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        estado: EstadoItemActualizable,
    ) -> CompraGuiadaDetalle | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE progreso_item pi
                    SET estado = %s::estado_item,
                        fecha_actualizacion = now()
                    FROM compra_guiada cg
                    JOIN carrito_distribuido cd ON cd.id = cg.carrito_distribuido_id
                    JOIN carrito c ON c.id = cd.carrito_id
                    WHERE pi.compra_guiada_id = cg.id
                      AND c.usuario_id = %s
                      AND cg.id = %s
                      AND cg.fecha_cierre IS NULL
                      AND pi.id = %s
                    RETURNING pi.id
                    """,
                    (estado, usuario_id, compra_id, progreso_item_id),
                )
                row = cur.fetchone()
                conn.commit()
                if row is None:
                    return None

        return self.obtener(usuario_id, compra_id)

    def buscar_alternativas_faltante(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
    ) -> list[AlternativaFaltante]:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    WITH objetivo AS (
                        SELECT
                            pi.id AS progreso_item_id,
                            pi.sucursal_actual_id,
                            ia.precio_unitario AS precio_original,
                            ia.subtotal AS subtotal_original,
                            ia.cantidad,
                            c.id AS carrito_id,
                            ic.id AS item_carrito_id,
                            ic.producto_id,
                            p.nombre AS producto_nombre,
                            p.marca AS producto_marca,
                            cd.id AS carrito_distribuido_id,
                            cd.cfg_preferencia,
                            cd.cfg_origen_geo,
                            cd.cfg_radio_km,
                            r.id AS ruteo_id
                        FROM progreso_item pi
                        JOIN compra_guiada cg ON cg.id = pi.compra_guiada_id
                        JOIN carrito_distribuido cd ON cd.id = cg.carrito_distribuido_id
                        JOIN carrito c ON c.id = cd.carrito_id
                        JOIN item_asignado ia ON ia.id = pi.item_asignado_id
                        JOIN item_carrito ic ON ic.id = ia.item_carrito_id
                        JOIN producto p ON p.id = ic.producto_id
                        LEFT JOIN ruteo r ON r.carrito_distribuido_id = cd.id
                        WHERE c.usuario_id = %s
                          AND cg.id = %s
                          AND cg.fecha_cierre IS NULL
                          AND pi.id = %s
                    )
                    SELECT
                        'MISMO_PRODUCTO'::text AS tipo,
                        1.0::double precision AS similitud_producto,
                        pr.id AS precio_id,
                        p.id AS producto_id,
                        p.nombre AS producto_nombre,
                        p.url_imagen,
                        s.id AS sucursal_id,
                        COALESCE(s.nombre, co.razon_social) AS sucursal,
                        co.razon_social AS comercio,
                        s.direccion,
                        s.localidad,
                        s.provincia,
                        b.nombre AS bandera_nombre,
                        b.url_logo AS bandera_logo_url,
                        pr.valor AS precio_unitario,
                        pr.valor * o.cantidad AS subtotal,
                        (pr.valor * o.cantidad) - o.subtotal_original AS diferencia_precio,
                        ST_Distance(s.geo, o.cfg_origen_geo) / 1000 AS distancia_km,
                        EXISTS (
                            SELECT 1 FROM parada pa
                            WHERE pa.ruteo_id = o.ruteo_id
                              AND pa.sucursal_id = s.id
                        ) AS esta_en_recorrido,
                        o.cfg_preferencia
                    FROM objetivo o
                    JOIN precio pr ON pr.producto_id = o.producto_id
                    JOIN producto p ON p.id = o.producto_id
                    JOIN sucursal s ON s.id = pr.sucursal_id
                    JOIN comercio co ON co.id = s.comercio_id
                    LEFT JOIN bandera b ON b.id = s.bandera_id
                    WHERE s.geo IS NOT NULL
                      AND s.id <> o.sucursal_actual_id
                      AND ST_DWithin(
                            s.geo, o.cfg_origen_geo, o.cfg_radio_km * 1000
                      )
                      AND pr.fecha_vigencia = (
                            SELECT MAX(pr2.fecha_vigencia)
                            FROM precio pr2
                            WHERE pr2.producto_id = pr.producto_id
                              AND pr2.sucursal_id = pr.sucursal_id
                      )
                    ORDER BY
                        EXISTS (
                            SELECT 1 FROM parada pa
                            WHERE pa.ruteo_id = o.ruteo_id
                              AND pa.sucursal_id = s.id
                        ) DESC,
                        CASE
                            WHEN o.cfg_preferencia = 'MENOR_DESPLAZAMIENTO'
                            THEN ST_Distance(s.geo, o.cfg_origen_geo) / 1000
                        END ASC NULLS LAST,
                        CASE
                            WHEN o.cfg_preferencia = 'MENOR_PRECIO' THEN pr.valor
                        END ASC,
                        ABS((pr.valor * o.cantidad) - o.subtotal_original) ASC,
                        pr.valor ASC,
                        ST_Distance(s.geo, o.cfg_origen_geo) / 1000 ASC NULLS LAST
                    LIMIT 6
                    """,
                    (usuario_id, compra_id, progreso_item_id),
                )
                rows = cur.fetchall()

        return [
            AlternativaFaltante(
                tipo=_normalizar_tipo_alternativa(str(row["tipo"])),
                precio_id=_to_int(row["precio_id"]),
                producto_id=_to_int(row["producto_id"]),
                nombre_producto=str(row["producto_nombre"]),
                url_imagen=str(row["url_imagen"]) if row["url_imagen"] is not None else None,
                sucursal_id=_to_int(row["sucursal_id"]),
                sucursal=str(row["sucursal"]),
                comercio=str(row["comercio"]),
                direccion=str(row["direccion"]) if row["direccion"] is not None else None,
                localidad=str(row["localidad"]) if row["localidad"] is not None else None,
                provincia=str(row["provincia"]) if row["provincia"] is not None else None,
                bandera_nombre=str(row["bandera_nombre"])
                if row["bandera_nombre"] is not None
                else None,
                bandera_logo_url=str(row["bandera_logo_url"])
                if row["bandera_logo_url"] is not None
                else None,
                precio_unitario=_to_float(row["precio_unitario"]) or 0.0,
                subtotal=_to_float(row["subtotal"]) or 0.0,
                diferencia_precio=_to_float(row["diferencia_precio"]) or 0.0,
                distancia_km=_to_float(row["distancia_km"]),
                esta_en_recorrido=bool(row["esta_en_recorrido"]),
                requiere_nueva_parada=not bool(row["esta_en_recorrido"]),
                confianza=_confianza_alternativa(str(row["tipo"])),
                motivo=_motivo_alternativa(str(row["tipo"]), bool(row["esta_en_recorrido"])),
            )
            for row in rows
        ]

    def aplicar_alternativa_faltante(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        precio_id: int,
    ) -> CompraGuiadaDetalle | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        pi.item_asignado_id,
                        ia.asignacion_sucursal_id AS asignacion_origen_id,
                        ia.item_carrito_id,
                        ia.cantidad,
                        c.id AS carrito_id,
                        cd.id AS carrito_distribuido_id,
                        cd.cfg_radio_km,
                        cd.cfg_origen_lat,
                        cd.cfg_origen_lon,
                        r.id AS ruteo_id
                    FROM progreso_item pi
                    JOIN compra_guiada cg ON cg.id = pi.compra_guiada_id
                    JOIN carrito_distribuido cd ON cd.id = cg.carrito_distribuido_id
                    JOIN carrito c ON c.id = cd.carrito_id
                    JOIN item_asignado ia ON ia.id = pi.item_asignado_id
                    LEFT JOIN ruteo r ON r.carrito_distribuido_id = cd.id
                    WHERE c.usuario_id = %s
                      AND cg.id = %s
                      AND cg.fecha_cierre IS NULL
                      AND pi.id = %s
                    FOR UPDATE OF pi, ia
                    """,
                    (usuario_id, compra_id, progreso_item_id),
                )
                objetivo = cur.fetchone()
                if objetivo is None:
                    conn.rollback()
                    return None

                cur.execute(
                    """
                    SELECT
                        pr.id AS precio_id,
                        pr.producto_id,
                        pr.valor AS precio_unitario,
                        s.id AS sucursal_id,
                        ST_Distance(
                            s.geo,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        ) / 1000 AS distancia_km
                    FROM precio pr
                    JOIN sucursal s ON s.id = pr.sucursal_id
                    WHERE pr.id = %s
                      AND s.geo IS NOT NULL
                      AND NOT EXISTS (
                            SELECT 1
                            FROM item_carrito ic_existente
                            WHERE ic_existente.carrito_id = %s
                              AND ic_existente.producto_id = pr.producto_id
                              AND ic_existente.id <> %s
                      )
                      AND ST_DWithin(
                            s.geo,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                            %s * 1000
                      )
                    """,
                    (
                        objetivo["cfg_origen_lon"],
                        objetivo["cfg_origen_lat"],
                        precio_id,
                        objetivo["carrito_id"],
                        objetivo["item_carrito_id"],
                        objetivo["cfg_origen_lon"],
                        objetivo["cfg_origen_lat"],
                        objetivo["cfg_radio_km"],
                    ),
                )
                alternativa = cur.fetchone()
                if alternativa is None:
                    conn.rollback()
                    return None

                carrito_distribuido_id = _to_int(objetivo["carrito_distribuido_id"])
                sucursal_id = _to_int(alternativa["sucursal_id"])
                asignacion_origen_id = _to_int(objetivo["asignacion_origen_id"])
                cantidad = _to_int(objetivo["cantidad"])
                precio_unitario = _to_float(alternativa["precio_unitario"]) or 0.0
                subtotal = round(precio_unitario * cantidad, 2)

                cur.execute(
                    """
                    SELECT id
                    FROM asignacion_sucursal
                    WHERE carrito_distribuido_id = %s AND sucursal_id = %s
                    """,
                    (carrito_distribuido_id, sucursal_id),
                )
                asignacion_destino = cur.fetchone()
                if asignacion_destino is None:
                    cur.execute(
                        """
                        INSERT INTO asignacion_sucursal (
                            carrito_distribuido_id,
                            sucursal_id,
                            subtotal
                        )
                        VALUES (%s, %s, 0)
                        RETURNING id
                        """,
                        (carrito_distribuido_id, sucursal_id),
                    )
                    asignacion_destino = cur.fetchone()
                    if asignacion_destino is None:
                        raise RuntimeError("No se pudo crear asignación para alternativa")
                asignacion_destino_id = _to_int(asignacion_destino["id"])

                cur.execute(
                    """
                    UPDATE item_carrito
                    SET producto_id = %s
                    WHERE id = %s
                    """,
                    (alternativa["producto_id"], objetivo["item_carrito_id"]),
                )
                cur.execute(
                    """
                    UPDATE item_asignado
                    SET asignacion_sucursal_id = %s,
                        precio_id = %s,
                        precio_unitario = %s,
                        subtotal = %s
                    WHERE id = %s
                    """,
                    (
                        asignacion_destino_id,
                        precio_id,
                        precio_unitario,
                        subtotal,
                        objetivo["item_asignado_id"],
                    ),
                )
                cur.execute(
                    """
                    UPDATE progreso_item
                    SET estado = 'PENDIENTE'::estado_item,
                        sucursal_actual_id = %s,
                        fecha_actualizacion = now()
                    WHERE id = %s
                    """,
                    (sucursal_id, progreso_item_id),
                )

                self._actualizar_subtotal_asignacion(cur, asignacion_origen_id)
                self._actualizar_subtotal_asignacion(cur, asignacion_destino_id)
                self._actualizar_costo_distribucion(cur, carrito_distribuido_id)
                self._asegurar_parada_adicional(
                    cur,
                    _to_int(objetivo["ruteo_id"]) if objetivo["ruteo_id"] is not None else None,
                    sucursal_id,
                    _to_float(alternativa["distancia_km"]) or 0.0,
                )
                conn.commit()

        return self.obtener(usuario_id, compra_id)

    def _actualizar_subtotal_asignacion(self, cur: Any, asignacion_id: int) -> None:
        cur.execute(
            """
            UPDATE asignacion_sucursal a
            SET subtotal = COALESCE((
                SELECT SUM(ia.subtotal)
                FROM item_asignado ia
                WHERE ia.asignacion_sucursal_id = a.id
            ), 0)
            WHERE a.id = %s
            """,
            (asignacion_id,),
        )

    def _actualizar_costo_distribucion(self, cur: Any, carrito_distribuido_id: int) -> None:
        cur.execute(
            """
            UPDATE carrito_distribuido cd
            SET costo_total_estimado = COALESCE((
                SELECT SUM(a.subtotal)
                FROM asignacion_sucursal a
                WHERE a.carrito_distribuido_id = cd.id
            ), 0)
            WHERE cd.id = %s
            """,
            (carrito_distribuido_id,),
        )

    def _asegurar_parada_adicional(
        self,
        cur: Any,
        ruteo_id: int | None,
        sucursal_id: int,
        distancia_km: float,
    ) -> None:
        if ruteo_id is None:
            return

        cur.execute(
            """
            SELECT id
            FROM parada
            WHERE ruteo_id = %s AND sucursal_id = %s
            """,
            (ruteo_id, sucursal_id),
        )
        if cur.fetchone() is not None:
            return

        cur.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 AS orden FROM parada WHERE ruteo_id = %s",
            (ruteo_id,),
        )
        orden_row = cur.fetchone()
        orden = _to_int(orden_row["orden"]) if orden_row is not None else 1
        distancia = round(distancia_km, 3)

        cur.execute(
            """
            INSERT INTO parada (
                ruteo_id,
                sucursal_id,
                orden,
                distancia_desde_anterior_km,
                es_origen,
                es_adicional
            ) VALUES (%s, %s, %s, %s, false, true)
            """,
            (ruteo_id, sucursal_id, orden, distancia),
        )
        cur.execute(
            """
            UPDATE ruteo
            SET distancia_total_km = distancia_total_km + %s
            WHERE id = %s
            """,
            (distancia, ruteo_id),
        )

    def finalizar(
        self,
        usuario_id: int,
        compra_id: int,
        estado_cierre: EstadoCierre,
    ) -> CompraGuiadaDetalle | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE compra_guiada cg
                    SET fecha_cierre = now(),
                        estado_cierre = %s::estado_cierre
                    FROM carrito_distribuido cd
                    JOIN carrito c ON c.id = cd.carrito_id
                    WHERE cd.id = cg.carrito_distribuido_id
                      AND c.usuario_id = %s
                      AND cg.id = %s
                      AND cg.fecha_cierre IS NULL
                    RETURNING cg.id
                    """,
                    (estado_cierre, usuario_id, compra_id),
                )
                row = cur.fetchone()
                conn.commit()
                if row is None:
                    return None

        return self.obtener(usuario_id, compra_id)


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


def _normalizar_estado_item(value: str) -> EstadoItem:
    if value not in {"PENDIENTE", "CONSEGUIDO", "NO_ENCONTRADO", "DESCARTADO"}:
        raise RuntimeError("Estado de item inválido")
    return cast(EstadoItem, value)


def _normalizar_estado_cierre(value: str) -> EstadoCierre:
    if value not in {"COMPLETADA", "INTERRUMPIDA"}:
        raise RuntimeError("Estado de cierre inválido")
    return cast(EstadoCierre, value)


def _normalizar_tipo_alternativa(value: str) -> TipoAlternativaFaltante:
    if value not in {"MISMO_PRODUCTO", "OTRA_PRESENTACION", "SUSTITUTO"}:
        raise RuntimeError("Tipo de alternativa inválido")
    return cast(TipoAlternativaFaltante, value)


def _confianza_alternativa(tipo: str) -> ConfianzaAlternativa:
    if tipo == "MISMO_PRODUCTO":
        return "ALTA"
    if tipo == "OTRA_PRESENTACION":
        return "MEDIA"
    return "BAJA"


def _motivo_alternativa(tipo: str, esta_en_recorrido: bool) -> str:
    ubicacion = "en una parada ya recomendada" if esta_en_recorrido else "en una sucursal cercana"
    if tipo == "MISMO_PRODUCTO":
        return f"Mismo producto {ubicacion}."
    if tipo == "OTRA_PRESENTACION":
        return f"Producto similar de la misma marca {ubicacion}."
    return f"Producto parecido y cercano al precio esperado {ubicacion}."
