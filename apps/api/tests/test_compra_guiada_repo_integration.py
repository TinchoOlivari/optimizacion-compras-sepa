from dataclasses import dataclass
from datetime import date
from time import time_ns

import psycopg
import pytest

from app.core.config import get_settings
from app.infra.compra_guiada_repo import CompraGuiadaRepository

LOCAL_DB_URL = "postgresql://tfg:tfg@localhost:5432/tfg"


def _db_disponible() -> bool:
    try:
        with psycopg.connect(LOCAL_DB_URL, connect_timeout=1):
            return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(
    not _db_disponible(),
    reason="PostgreSQL no accesible en localhost:5432; se omite integración.",
)


@dataclass(frozen=True)
class _SeedCompraGuiada:
    usuario_id: int
    carrito_id: int
    compra_id: int
    progreso_item_id: int
    producto_original_id: int
    producto_presentacion_id: int
    producto_sustituto_id: int
    precio_original_recorrido_id: int
    precio_sustituto_id: int
    sucursal_nueva_id: int
    productos_ids: tuple[int, ...]
    comercio_id: int


@pytest.fixture(autouse=True)
def _db_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", LOCAL_DB_URL)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_buscar_alternativas_faltante_devuelve_mismo_producto_en_otras_sucursales() -> None:
    seed = _seed_compra_guiada()
    try:
        alternativas = CompraGuiadaRepository().buscar_alternativas_faltante(
            seed.usuario_id,
            seed.compra_id,
            seed.progreso_item_id,
        )

        assert len(alternativas) >= 1
        assert alternativas[0].tipo == "MISMO_PRODUCTO"
        assert alternativas[0].precio_id == seed.precio_original_recorrido_id
        assert alternativas[0].esta_en_recorrido

        for alternativa in alternativas:
            assert alternativa.tipo == "MISMO_PRODUCTO"
            assert alternativa.precio_unitario > 0
    finally:
        _cleanup_seed(seed)


def test_aplicar_alternativa_sustituto_actualiza_item_asignado_y_agrega_parada() -> None:
    seed = _seed_compra_guiada()
    try:
        compra = CompraGuiadaRepository().aplicar_alternativa_faltante(
            seed.usuario_id,
            seed.compra_id,
            seed.progreso_item_id,
            seed.precio_sustituto_id,
        )

        assert compra is not None
        parada_sustituto = next(
            parada for parada in compra.paradas if parada.sucursal_id == seed.sucursal_nueva_id
        )
        assert parada_sustituto.es_adicional
        assert parada_sustituto.items[0].producto_id == seed.producto_sustituto_id
        assert parada_sustituto.items[0].estado == "PENDIENTE"

        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ic.producto_id, pi.sucursal_actual_id, ia.precio_id
                    FROM progreso_item pi
                    JOIN item_asignado ia ON ia.id = pi.item_asignado_id
                    JOIN item_carrito ic ON ic.id = ia.item_carrito_id
                    WHERE pi.id = %s
                    """,
                    (seed.progreso_item_id,),
                )
                row = cur.fetchone()
                assert row is not None
                assert int(row[0]) == seed.producto_sustituto_id
                assert int(row[1]) == seed.sucursal_nueva_id
                assert int(row[2]) == seed.precio_sustituto_id
    finally:
        _cleanup_seed(seed)


def _seed_compra_guiada() -> _SeedCompraGuiada:
    token = str(time_ns())[-10:]
    correo = f"compra-guiada-{token}@test.com"
    cuit = f"{int(token[-9:]) + 10_000_000:011d}"[-11:]

    with psycopg.connect(LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuario (nombre, correo, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                ("Usuario Compra Guiada", correo, "hash"),
            )
            usuario_id = _one_id(cur)

            cur.execute(
                """
                INSERT INTO carrito (usuario_id, titulo, activo)
                VALUES (%s, %s, true)
                RETURNING id
                """,
                (usuario_id, "Carrito Compra Guiada"),
            )
            carrito_id = _one_id(cur)

            cur.execute(
                """
                INSERT INTO comercio (cuit, razon_social)
                VALUES (%s, %s)
                RETURNING id
                """,
                (cuit, f"Comercio Compra Guiada {token}"),
            )
            comercio_id = _one_id(cur)

            sucursal_actual_id = _insert_sucursal(cur, comercio_id, token, "1", "Sucursal Actual")
            sucursal_recorrido_id = _insert_sucursal(
                cur,
                comercio_id,
                token,
                "2",
                "Sucursal Recorrido",
            )
            sucursal_nueva_id = _insert_sucursal(cur, comercio_id, token, "3", "Sucursal Nueva")

            producto_original_id = _insert_producto(
                cur,
                token,
                "0",
                "Leche entera larga vida 1L",
                "La Serenisima",
                "1 L",
            )
            producto_presentacion_id = _insert_producto(
                cur,
                token,
                "1",
                "Leche entera larga vida 2L",
                "La Serenisima",
                "2 L",
            )
            producto_sustituto_id = _insert_producto(
                cur,
                token,
                "2",
                "Leche parcialmente descremada 1L",
                "Milkaut",
                "1 L",
            )

            cur.execute(
                """
                INSERT INTO item_carrito (carrito_id, producto_id, cantidad)
                VALUES (%s, %s, 1)
                RETURNING id
                """,
                (carrito_id, producto_original_id),
            )
            item_carrito_id = _one_id(cur)

            precio_actual_id = _insert_precio(cur, producto_original_id, sucursal_actual_id, 1000)
            precio_original_recorrido_id = _insert_precio(
                cur,
                producto_original_id,
                sucursal_recorrido_id,
                1050,
            )
            _insert_precio(cur, producto_presentacion_id, sucursal_nueva_id, 1800)
            precio_sustituto_id = _insert_precio(cur, producto_sustituto_id, sucursal_nueva_id, 980)

            cur.execute(
                """
                INSERT INTO carrito_distribuido (
                    carrito_id,
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
                    %s, 1000, NULL, true, 10, 3, 'BALANCEADO', -31.4, -64.1,
                    ST_SetSRID(ST_MakePoint(-64.1, -31.4), 4326)::geography
                )
                RETURNING id
                """,
                (carrito_id,),
            )
            carrito_distribuido_id = _one_id(cur)

            cur.execute(
                """
                INSERT INTO asignacion_sucursal (carrito_distribuido_id, sucursal_id, subtotal)
                VALUES (%s, %s, 1000)
                RETURNING id
                """,
                (carrito_distribuido_id, sucursal_actual_id),
            )
            asignacion_id = _one_id(cur)

            cur.execute(
                """
                INSERT INTO item_asignado (
                    asignacion_sucursal_id,
                    item_carrito_id,
                    precio_id,
                    cantidad,
                    precio_unitario,
                    subtotal
                ) VALUES (%s, %s, %s, 1, 1000, 1000)
                RETURNING id
                """,
                (asignacion_id, item_carrito_id, precio_actual_id),
            )
            item_asignado_id = _one_id(cur)

            cur.execute(
                """
                INSERT INTO ruteo (carrito_distribuido_id, distancia_total_km)
                VALUES (%s, 2.0)
                RETURNING id
                """,
                (carrito_distribuido_id,),
            )
            ruteo_id = _one_id(cur)

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
                ) VALUES (%s, NULL, 0, 0, true, false, -31.4, -64.1)
                """,
                (ruteo_id,),
            )
            cur.execute(
                """
                INSERT INTO parada (
                    ruteo_id,
                    sucursal_id,
                    orden,
                    distancia_desde_anterior_km,
                    es_origen,
                    es_adicional
                ) VALUES (%s, %s, 1, 1.0, false, false), (%s, %s, 2, 1.0, false, false)
                """,
                (ruteo_id, sucursal_actual_id, ruteo_id, sucursal_recorrido_id),
            )

            cur.execute(
                """
                INSERT INTO compra_guiada (carrito_distribuido_id)
                VALUES (%s)
                RETURNING id
                """,
                (carrito_distribuido_id,),
            )
            compra_id = _one_id(cur)

            cur.execute(
                """
                INSERT INTO progreso_item (
                    compra_guiada_id,
                    item_asignado_id,
                    estado,
                    sucursal_actual_id
                ) VALUES (%s, %s, 'NO_ENCONTRADO'::estado_item, %s)
                RETURNING id
                """,
                (compra_id, item_asignado_id, sucursal_actual_id),
            )
            progreso_item_id = _one_id(cur)
        conn.commit()

    return _SeedCompraGuiada(
        usuario_id=usuario_id,
        carrito_id=carrito_id,
        compra_id=compra_id,
        progreso_item_id=progreso_item_id,
        producto_original_id=producto_original_id,
        producto_presentacion_id=producto_presentacion_id,
        producto_sustituto_id=producto_sustituto_id,
        precio_original_recorrido_id=precio_original_recorrido_id,
        precio_sustituto_id=precio_sustituto_id,
        sucursal_nueva_id=sucursal_nueva_id,
        productos_ids=(producto_original_id, producto_presentacion_id, producto_sustituto_id),
        comercio_id=comercio_id,
    )


def _insert_sucursal(
    cur: psycopg.Cursor,
    comercio_id: int,
    token: str,
    suffix: str,
    nombre: str,
) -> int:
    lat = -31.40 - (int(suffix) * 0.01)
    lon = -64.10 - (int(suffix) * 0.01)
    cur.execute(
        """
        INSERT INTO sucursal (
            comercio_id,
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
        ) VALUES (
            %s, %s, %s, %s, %s, %s, 'Cordoba', 'X', %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        )
        RETURNING id
        """,
        (
            comercio_id,
            f"C{token}{suffix}",
            f"B{token}{suffix}",
            f"S{token}{suffix}",
            nombre,
            f"Calle {suffix}",
            lat,
            lon,
            lon,
            lat,
        ),
    )
    return _one_id(cur)


def _insert_producto(
    cur: psycopg.Cursor,
    token: str,
    suffix: str,
    nombre: str,
    marca: str,
    presentacion: str,
) -> int:
    cur.execute(
        """
        INSERT INTO producto (codigo_ean, nombre, marca, presentacion)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (f"779{token[-10:]}{suffix}"[-14:], nombre, marca, presentacion),
    )
    return _one_id(cur)


def _insert_precio(cur: psycopg.Cursor, producto_id: int, sucursal_id: int, valor: int) -> int:
    cur.execute(
        """
        INSERT INTO precio (producto_id, sucursal_id, valor, fecha_vigencia)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (producto_id, sucursal_id, valor, date.today()),
    )
    return _one_id(cur)


def _cleanup_seed(seed: _SeedCompraGuiada) -> None:
    with psycopg.connect(LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM carrito_distribuido
                WHERE carrito_id IN (
                    SELECT id
                    FROM carrito
                    WHERE usuario_id = %s
                )
                """,
                (seed.usuario_id,),
            )
            cur.execute("DELETE FROM usuario WHERE id = %s", (seed.usuario_id,))
            cur.execute("DELETE FROM producto WHERE id = ANY(%s)", (list(seed.productos_ids),))
            cur.execute("DELETE FROM comercio WHERE id = %s", (seed.comercio_id,))
        conn.commit()


def _one_id(cur: psycopg.Cursor) -> int:
    row = cur.fetchone()
    assert row is not None
    return int(row[0])
