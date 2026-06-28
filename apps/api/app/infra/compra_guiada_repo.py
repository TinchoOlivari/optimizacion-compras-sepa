from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from psycopg.rows import dict_row

from app.domain.compra_guiada import (
    CompraGuiadaDetalle,
    CompraGuiadaNotFoundError,
    EstadoCierre,
    EstadoItem,
    EstadoItemActualizable,
    EstadoItemTerminal,
    ICompraGuiadaRepository,
    ItemCompraGuiada,
    ParadaCompraGuiada,
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
                        COALESCE(pa.distancia_desde_anterior_km, 0) AS distancia_desde_anterior_km
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
