from datetime import UTC, datetime
from typing import Any

from psycopg.rows import dict_row

from app.domain.ports import (
    Carrito,
    EliminacionCarrito,
    ICarritoRepository,
    ItemCarrito,
    ProductoResumen,
)
from app.infra.db import get_connection


class CarritoRepository(ICarritoRepository):
    def listar_carritos(self, usuario_id: int) -> list[Carrito]:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        c.id,
                        c.usuario_id,
                        c.titulo,
                        c.activo,
                        c.fecha_ultima_edicion,
                        COUNT(ic.id)::int AS cantidad_items
                    FROM carrito c
                    LEFT JOIN item_carrito ic ON ic.carrito_id = c.id
                    WHERE c.usuario_id = %s
                    GROUP BY c.id
                    ORDER BY c.fecha_ultima_edicion DESC
                    """,
                    (usuario_id,),
                )
                rows = cur.fetchall()
                return [_map_carrito(row) for row in rows]

    def crear_carrito_activo(self, usuario_id: int, titulo: str | None = None) -> Carrito:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE carrito SET activo = false WHERE usuario_id = %s AND activo = true",
                    (usuario_id,),
                )
                cur.execute(
                    """
                    INSERT INTO carrito (usuario_id, titulo, activo)
                    VALUES (%s, %s, true)
                    RETURNING id
                    """,
                    (usuario_id, titulo),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No se pudo crear el carrito")
                carrito_id = int(row[0])
                conn.commit()
        carrito = self.obtener_carrito(usuario_id, carrito_id)
        if carrito is None:
            raise RuntimeError("No se pudo recuperar el carrito creado")
        return carrito

    def obtener_carrito(self, usuario_id: int, carrito_id: int) -> Carrito | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        c.id,
                        c.usuario_id,
                        c.titulo,
                        c.activo,
                        c.fecha_ultima_edicion,
                        COUNT(ic.id)::int AS cantidad_items
                    FROM carrito c
                    LEFT JOIN item_carrito ic ON ic.carrito_id = c.id
                    WHERE c.usuario_id = %s AND c.id = %s
                    GROUP BY c.id
                    """,
                    (usuario_id, carrito_id),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return _map_carrito(row)

    def actualizar_titulo(
        self,
        usuario_id: int,
        carrito_id: int,
        titulo: str | None,
    ) -> Carrito | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE carrito
                    SET titulo = %s,
                        fecha_ultima_edicion = now()
                    WHERE id = %s AND usuario_id = %s
                    """,
                    (titulo, carrito_id, usuario_id),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    return None
                conn.commit()
        return self.obtener_carrito(usuario_id, carrito_id)

    def activar_carrito(self, usuario_id: int, carrito_id: int) -> Carrito | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM carrito WHERE id = %s AND usuario_id = %s",
                    (carrito_id, usuario_id),
                )
                if cur.fetchone() is None:
                    conn.rollback()
                    return None

                cur.execute(
                    "UPDATE carrito SET activo = false WHERE usuario_id = %s AND activo = true",
                    (usuario_id,),
                )
                cur.execute(
                    """
                    UPDATE carrito
                    SET activo = true,
                        fecha_ultima_edicion = now()
                    WHERE id = %s AND usuario_id = %s
                    """,
                    (carrito_id, usuario_id),
                )
                conn.commit()
        return self.obtener_carrito(usuario_id, carrito_id)

    def eliminar_carrito(self, usuario_id: int, carrito_id: int) -> EliminacionCarrito:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT id FROM carrito WHERE id = %s AND usuario_id = %s",
                    (carrito_id, usuario_id),
                )
                if cur.fetchone() is None:
                    return EliminacionCarrito(eliminado=False, era_activo=False)

                self._eliminar_distribuciones_carrito(cur, carrito_id)
                cur.execute(
                    """
                    DELETE FROM carrito
                    WHERE id = %s AND usuario_id = %s
                    RETURNING activo
                    """,
                    (carrito_id, usuario_id),
                )
                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    return EliminacionCarrito(eliminado=False, era_activo=False)
                conn.commit()
                return EliminacionCarrito(eliminado=True, era_activo=bool(row["activo"]))

    def promover_activo_o_crear(self, usuario_id: int) -> Carrito:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE carrito SET activo = false WHERE usuario_id = %s AND activo = true",
                    (usuario_id,),
                )
                cur.execute(
                    """
                    UPDATE carrito
                    SET activo = true,
                        fecha_ultima_edicion = now()
                    WHERE id = (
                        SELECT id
                        FROM carrito
                        WHERE usuario_id = %s
                        ORDER BY fecha_ultima_edicion DESC
                        LIMIT 1
                    )
                    RETURNING id
                    """,
                    (usuario_id,),
                )
                row = cur.fetchone()
                if row is None:
                    conn.commit()
                    raise RuntimeError("No hay carritos para promover")
                carrito_id = int(row[0])
                conn.commit()

        carrito = self.obtener_carrito(usuario_id, carrito_id)
        if carrito is None:
            raise RuntimeError("No se pudo recuperar carrito activo")
        return carrito

    def obtener_item_por_producto(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
    ) -> ItemCarrito | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT ic.id, ic.carrito_id, ic.producto_id, ic.cantidad
                    FROM item_carrito ic
                    INNER JOIN carrito c ON c.id = ic.carrito_id
                    WHERE c.usuario_id = %s AND c.id = %s AND ic.producto_id = %s
                    """,
                    (usuario_id, carrito_id, producto_id),
                )
                row = cur.fetchone()
                return _map_item(row)

    def agregar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
        cantidad: int,
    ) -> ItemCarrito:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                self._assert_carrito_usuario(cur, usuario_id, carrito_id)
                self._assert_producto_existe(cur, producto_id)
                self._eliminar_distribuciones_carrito(cur, carrito_id)

                cur.execute(
                    """
                    INSERT INTO item_carrito (carrito_id, producto_id, cantidad)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (carrito_id, producto_id)
                    DO UPDATE SET cantidad = LEAST(item_carrito.cantidad + EXCLUDED.cantidad, 99)
                    RETURNING id, carrito_id, producto_id, cantidad
                    """,
                    (carrito_id, producto_id, cantidad),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No se pudo agregar ítem al carrito")

                cur.execute(
                    "UPDATE carrito SET fecha_ultima_edicion = now() WHERE id = %s",
                    (carrito_id,),
                )
                conn.commit()
                return _map_item_required(row)

    def actualizar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        item_id: int,
        cantidad: int,
    ) -> ItemCarrito | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                self._assert_carrito_usuario(cur, usuario_id, carrito_id)
                self._eliminar_distribuciones_carrito(cur, carrito_id)
                cur.execute(
                    """
                    UPDATE item_carrito
                    SET cantidad = %s
                    WHERE id = %s AND carrito_id = %s
                    RETURNING id, carrito_id, producto_id, cantidad
                    """,
                    (cantidad, item_id, carrito_id),
                )
                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    return None

                cur.execute(
                    "UPDATE carrito SET fecha_ultima_edicion = now() WHERE id = %s",
                    (carrito_id,),
                )
                conn.commit()
                return _map_item_required(row)

    def eliminar_item(self, usuario_id: int, carrito_id: int, item_id: int) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                self._assert_carrito_usuario(cur, usuario_id, carrito_id)
                self._eliminar_distribuciones_carrito(cur, carrito_id)
                cur.execute(
                    "DELETE FROM item_carrito WHERE id = %s AND carrito_id = %s",
                    (item_id, carrito_id),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    return False
                cur.execute(
                    "UPDATE carrito SET fecha_ultima_edicion = now() WHERE id = %s",
                    (carrito_id,),
                )
                conn.commit()
                return True

    def listar_items_con_producto(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> list[tuple[ItemCarrito, ProductoResumen | None]]:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        ic.id,
                        ic.carrito_id,
                        ic.producto_id,
                        ic.cantidad,
                        p.id AS producto_existente_id,
                        p.codigo_ean,
                        p.nombre,
                        p.marca,
                        p.presentacion,
                        p.url_imagen
                    FROM item_carrito ic
                    INNER JOIN carrito c ON c.id = ic.carrito_id
                    LEFT JOIN producto p ON p.id = ic.producto_id
                    WHERE c.usuario_id = %s AND c.id = %s
                    ORDER BY ic.id
                    """,
                    (usuario_id, carrito_id),
                )
                rows = cur.fetchall()

        return [_map_item_con_producto(row) for row in rows]

    @staticmethod
    def _eliminar_distribuciones_carrito(cur: Any, carrito_id: int) -> None:
        cursor: Any = cur
        cursor.execute(
            "DELETE FROM carrito_distribuido WHERE carrito_id = %s",
            (carrito_id,),
        )

    @staticmethod
    def _assert_carrito_usuario(cur: Any, usuario_id: int, carrito_id: int) -> None:
        cursor: Any = cur
        cursor.execute(
            "SELECT id FROM carrito WHERE id = %s AND usuario_id = %s",
            (carrito_id, usuario_id),
        )
        if cursor.fetchone() is None:
            raise RuntimeError("Carrito no encontrado o sin permisos")

    @staticmethod
    def _assert_producto_existe(cur: Any, producto_id: int) -> None:
        cursor: Any = cur
        cursor.execute("SELECT id FROM producto WHERE id = %s", (producto_id,))
        if cursor.fetchone() is None:
            raise RuntimeError("Producto no encontrado")


def _map_carrito(row: dict[str, Any]) -> Carrito:
    fecha_raw = row["fecha_ultima_edicion"]
    if isinstance(fecha_raw, datetime):
        fecha_ultima_edicion = fecha_raw
    else:
        fecha_ultima_edicion = datetime.fromisoformat(str(fecha_raw)).replace(tzinfo=UTC)

    return Carrito(
        id=int(row["id"]),
        usuario_id=int(row["usuario_id"]),
        titulo=str(row["titulo"]) if row["titulo"] is not None else None,
        activo=bool(row["activo"]),
        fecha_ultima_edicion=fecha_ultima_edicion,
        cantidad_items=int(row["cantidad_items"]),
    )


def _map_item(row: dict[str, Any] | None) -> ItemCarrito | None:
    if row is None:
        return None
    return _map_item_required(row)


def _map_item_required(row: dict[str, Any]) -> ItemCarrito:
    return ItemCarrito(
        id=int(row["id"]),
        carrito_id=int(row["carrito_id"]),
        producto_id=int(row["producto_id"]),
        cantidad=int(row["cantidad"]),
    )


def _map_item_con_producto(row: dict[str, Any]) -> tuple[ItemCarrito, ProductoResumen | None]:
    item = _map_item_required(row)
    if row["producto_existente_id"] is None:
        return item, None

    producto = ProductoResumen(
        id=int(row["producto_existente_id"]),
        codigo_ean=str(row["codigo_ean"]),
        nombre=str(row["nombre"]),
        marca=str(row["marca"]) if row["marca"] is not None else None,
        presentacion=str(row["presentacion"]) if row["presentacion"] is not None else None,
        url_imagen=str(row["url_imagen"]) if row["url_imagen"] is not None else None,
    )
    return item, producto
