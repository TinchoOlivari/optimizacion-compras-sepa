from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from time import perf_counter

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_current_user
from app.api.v1.preferencias import get_distribucion_service
from app.core.config import get_settings
from app.domain.optimizacion import (
    AsignacionSucursalResultado,
    EntradaOptimizacion,
    ItemAsignadoResultado,
    ItemNoAsignadoResultado,
    OfertaItemCandidata,
)
from app.domain.servicios.distribucion import DistribucionService
from app.infra.distribucion_repo import DistribucionRepository, PreferenciasRepository
from app.main import app

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
class _SeedContext:
    usuario_id: int
    carrito_id: int
    comercio_id: int | None
    sucursal_id: int | None
    producto_ids: tuple[int, ...]
    precio_ids: tuple[int, ...]


@dataclass
class _AgrupadoSucursal:
    sucursal: str
    comercio: str
    direccion: str | None
    localidad: str | None
    provincia: str | None
    latitud: float
    longitud: float
    items: list[ItemAsignadoResultado]
    subtotal: float


class _MotorDeterministico:
    def distribuir(
        self,
        entrada: EntradaOptimizacion,
    ) -> tuple[list[AsignacionSucursalResultado], list[ItemNoAsignadoResultado]]:
        ofertas_por_item: dict[int, list[OfertaItemCandidata]] = {}
        for oferta in entrada.ofertas:
            ofertas_por_item.setdefault(oferta.item_carrito_id, []).append(oferta)

        agrupado_por_sucursal: dict[int, _AgrupadoSucursal] = {}
        no_asignados: list[ItemNoAsignadoResultado] = []

        for item in entrada.items:
            opciones = ofertas_por_item.get(item.item_carrito_id, [])
            if not opciones:
                no_asignados.append(
                    ItemNoAsignadoResultado(
                        item_carrito_id=item.item_carrito_id,
                        producto_id=item.producto_id,
                        nombre_producto=item.nombre_producto,
                        cantidad=item.cantidad,
                    )
                )
                continue

            mejor = min(opciones, key=lambda oferta: oferta.precio_unitario)
            subtotal = round(float(mejor.precio_unitario) * item.cantidad, 2)

            if mejor.sucursal_id not in agrupado_por_sucursal:
                agrupado_por_sucursal[mejor.sucursal_id] = _AgrupadoSucursal(
                    sucursal=mejor.sucursal,
                    comercio=mejor.comercio,
                    direccion=mejor.direccion,
                    localidad=mejor.localidad,
                    provincia=mejor.provincia,
                    latitud=mejor.latitud,
                    longitud=mejor.longitud,
                    items=[],
                    subtotal=0.0,
                )

            agrupado = agrupado_por_sucursal[mejor.sucursal_id]
            agrupado.items.append(
                ItemAsignadoResultado(
                    item_carrito_id=item.item_carrito_id,
                    producto_id=item.producto_id,
                    nombre_producto=item.nombre_producto,
                    cantidad=item.cantidad,
                    precio_id=mejor.precio_id,
                    precio_unitario=mejor.precio_unitario,
                    subtotal=subtotal,
                )
            )
            agrupado.subtotal = round(agrupado.subtotal + subtotal, 2)

        asignaciones = [
            AsignacionSucursalResultado(
                sucursal_id=sucursal_id,
                sucursal=agrupado.sucursal,
                comercio=agrupado.comercio,
                direccion=agrupado.direccion,
                localidad=agrupado.localidad,
                provincia=agrupado.provincia,
                latitud=agrupado.latitud,
                longitud=agrupado.longitud,
                subtotal=agrupado.subtotal,
                items=agrupado.items,
            )
            for sucursal_id, agrupado in sorted(agrupado_por_sucursal.items())
        ]
        return asignaciones, no_asignados


class _OsrmDeterministico:
    def obtener_matriz_km(self, puntos: list[tuple[float, float]]) -> list[list[float]]:
        size = len(puntos)
        matriz: list[list[float]] = []
        for i in range(size):
            fila: list[float] = []
            for j in range(size):
                if i == j:
                    fila.append(0.0)
                else:
                    fila.append(0.8)
            matriz.append(fila)
        return matriz


class _OsrmRutaInvertida:
    def obtener_matriz_km(self, puntos: list[tuple[float, float]]) -> list[list[float]]:
        size = len(puntos)
        matriz = [[0.0 for _ in range(size)] for _ in range(size)]
        if size > 1:
            matriz[0][1] = 5.0
            matriz[1][0] = 5.0
        if size > 2:
            matriz[0][2] = 1.0
            matriz[2][0] = 1.0
            matriz[2][1] = 1.0
            matriz[1][2] = 6.0
        return matriz


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def _db_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", LOCAL_DB_URL)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _override_auth(usuario_id: int) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": usuario_id,
        "correo": f"user{usuario_id}@test.com",
        "nombre": "Usuario Test",
    }


def _override_real_service() -> None:
    app.dependency_overrides[get_distribucion_service] = lambda: DistribucionService(
        preferencias_repo=PreferenciasRepository(),
        distribucion_repo=DistribucionRepository(),
        motor=_MotorDeterministico(),
        osrm_client=_OsrmDeterministico(),
    )


def _seed_context(
    *,
    with_items: bool,
    preferencias_validas: bool,
    item_count: int = 1,
) -> _SeedContext:
    now = datetime.now(UTC)
    token = f"{int(now.timestamp() * 1_000_000)}"
    correo = f"seed-{token}@test.com"
    cuit = f"{int(token[-9:]) + 10_000_000:011d}"

    producto_ids: list[int] = []
    precio_ids: list[int] = []
    comercio_id: int | None = None
    sucursal_id: int | None = None

    with psycopg.connect(LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuario (nombre, correo, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                ("Usuario Seed", correo, "hash"),
            )
            row = cur.fetchone()
            assert row is not None
            usuario_id = int(row[0])

            cur.execute(
                """
                INSERT INTO carrito (usuario_id, titulo, activo)
                VALUES (%s, %s, true)
                RETURNING id
                """,
                (usuario_id, "Carrito Seed"),
            )
            row = cur.fetchone()
            assert row is not None
            carrito_id = int(row[0])

            if preferencias_validas:
                cur.execute(
                    """
                    INSERT INTO preferencias_optimizacion (
                        usuario_id,
                        radio_km,
                        max_paradas,
                        modo_preferencia,
                        ubicacion_referencia_lat,
                        ubicacion_referencia_lon,
                        ubicacion_referencia_geo
                    ) VALUES (
                        %s, 5, NULL, NULL, -31.4, -64.1,
                        ST_SetSRID(ST_MakePoint(-64.1, -31.4), 4326)::geography
                    )
                    """,
                    (usuario_id,),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO preferencias_optimizacion (
                        usuario_id,
                        radio_km,
                        max_paradas,
                        modo_preferencia,
                        ubicacion_referencia_lat,
                        ubicacion_referencia_lon,
                        ubicacion_referencia_geo
                    ) VALUES (%s, NULL, NULL, NULL, NULL, NULL, NULL)
                    """,
                    (usuario_id,),
                )

            if with_items:
                cur.execute(
                    """
                    INSERT INTO comercio (cuit, razon_social)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (cuit, f"Comercio Seed {token}"),
                )
                row = cur.fetchone()
                assert row is not None
                comercio_id = int(row[0])

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
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    )
                    RETURNING id
                    """,
                    (
                        comercio_id,
                        f"C{token}",
                        f"B{token}",
                        f"S{token}",
                        "Sucursal Seed",
                        "Calle Seed 123",
                        "Cordoba",
                        "X",
                        -31.41,
                        -64.12,
                        -64.12,
                        -31.41,
                    ),
                )
                row = cur.fetchone()
                assert row is not None
                sucursal_id = int(row[0])

                for idx in range(item_count):
                    codigo_ean = f"7790000{token[-6:]}{idx:01d}"[-13:]
                    cur.execute(
                        """
                        INSERT INTO producto (codigo_ean, nombre)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (codigo_ean, f"Producto Seed {idx}"),
                    )
                    row = cur.fetchone()
                    assert row is not None
                    producto_id = int(row[0])
                    producto_ids.append(producto_id)

                    cur.execute(
                        """
                        INSERT INTO item_carrito (carrito_id, producto_id, cantidad)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (carrito_id, producto_id, 1),
                    )
                    row = cur.fetchone()
                    assert row is not None
                    item_carrito_id = int(row[0])
                    _ = item_carrito_id

                    cur.execute(
                        """
                        INSERT INTO precio (producto_id, sucursal_id, valor, fecha_vigencia)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (producto_id, sucursal_id, 150.0 + idx, date.today()),
                    )
                    row = cur.fetchone()
                    assert row is not None
                    precio_ids.append(int(row[0]))

        conn.commit()

    return _SeedContext(
        usuario_id=usuario_id,
        carrito_id=carrito_id,
        comercio_id=comercio_id,
        sucursal_id=sucursal_id,
        producto_ids=tuple(producto_ids),
        precio_ids=tuple(precio_ids),
    )


def _cleanup_seed(context: _SeedContext) -> None:
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
                (context.usuario_id,),
            )
            cur.execute("DELETE FROM usuario WHERE id = %s", (context.usuario_id,))
            if context.producto_ids:
                cur.execute(
                    "DELETE FROM producto WHERE id = ANY(%s)",
                    (list(context.producto_ids),),
                )
            if context.comercio_id is not None:
                cur.execute("DELETE FROM comercio WHERE id = %s", (context.comercio_id,))
        conn.commit()


def _count_distribuciones(carrito_id: int) -> int:
    with psycopg.connect(LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM carrito_distribuido WHERE carrito_id = %s",
                (carrito_id,),
            )
            row = cur.fetchone()
            assert row is not None
            return int(row[0])


def _item_carrito_ids(carrito_id: int) -> list[int]:
    with psycopg.connect(LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM item_carrito WHERE carrito_id = %s ORDER BY id",
                (carrito_id,),
            )
            return [int(row[0]) for row in cur.fetchall()]


def test_distribuir_401_sin_auth(client: TestClient) -> None:
    response = client.post("/api/v1/carritos/123/distribuir")
    assert response.status_code == 401


def test_distribuir_409_carrito_vacio_con_db(client: TestClient) -> None:
    context = _seed_context(with_items=False, preferencias_validas=True)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        response = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")

        assert response.status_code == 409
        assert response.json()["detail"]["error"]["codigo"] == "CARRITO_VACIO"
    finally:
        _cleanup_seed(context)


def test_distribuir_422_config_incompleta_con_db(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=False)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        response = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")

        assert response.status_code == 422
        assert response.json()["detail"]["error"]["codigo"] == "CONFIG_INVALIDA"
    finally:
        _cleanup_seed(context)


def test_distribuir_persiste_unica_vigente_y_get_devuelve_ultima(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=True, item_count=2)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        first = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert first.status_code == 200
        first_cost = float(first.json()["costo_total_estimado"])

        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE precio SET valor = valor + 50 WHERE id = %s",
                    (context.precio_ids[0],),
                )
            conn.commit()

        second = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert second.status_code == 200
        second_cost = float(second.json()["costo_total_estimado"])
        assert second_cost > first_cost

        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT vigente
                    FROM carrito_distribuido
                    WHERE carrito_id = %s
                    ORDER BY id
                    """,
                    (context.carrito_id,),
                )
                vigencias = [bool(row[0]) for row in cur.fetchall()]

        assert len(vigencias) == 2
        assert vigencias.count(True) == 1
        assert vigencias[-1] is True

        actual = client.get(f"/api/v1/carritos/{context.carrito_id}/distribucion")
        assert actual.status_code == 200
        assert float(actual.json()["costo_total_estimado"]) == second_cost
    finally:
        _cleanup_seed(context)


def test_get_distribucion_ordenada_por_ruta_y_con_productos(client: TestClient) -> None:
    now = datetime.now(UTC)
    token = f"{int(now.timestamp() * 1_000_000)}"
    correo = f"route-{token}@test.com"
    cuit = f"{int(token[-9:]) + 20_000_000:011d}"
    producto_ids: list[int] = []
    comercio_id: int | None = None

    with psycopg.connect(LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuario (nombre, correo, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                ("Usuario Route", correo, "hash"),
            )
            row = cur.fetchone()
            assert row is not None
            usuario_id = int(row[0])

            cur.execute(
                """
                INSERT INTO carrito (usuario_id, titulo, activo)
                VALUES (%s, %s, true)
                RETURNING id
                """,
                (usuario_id, "Carrito Route"),
            )
            row = cur.fetchone()
            assert row is not None
            carrito_id = int(row[0])

            cur.execute(
                """
                INSERT INTO preferencias_optimizacion (
                    usuario_id,
                    radio_km,
                    max_paradas,
                    modo_preferencia,
                    ubicacion_referencia_lat,
                    ubicacion_referencia_lon,
                    ubicacion_referencia_geo
                ) VALUES (
                    %s, 10, 3, 'MENOR_PRECIO', -31.4, -64.1,
                    ST_SetSRID(ST_MakePoint(-64.1, -31.4), 4326)::geography
                )
                """,
                (usuario_id,),
            )

            cur.execute(
                """
                INSERT INTO comercio (cuit, razon_social)
                VALUES (%s, %s)
                RETURNING id
                """,
                (cuit, f"Comercio Route {token}"),
            )
            row = cur.fetchone()
            assert row is not None
            comercio_id = int(row[0])

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
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                )
                RETURNING id
                """,
                (
                    comercio_id,
                    f"C1{token}",
                    f"B1{token}",
                    f"S1{token}",
                    "Sucursal 1",
                    "Calle 1",
                    "Cordoba",
                    "X",
                    -31.40,
                    -64.10,
                    -64.10,
                    -31.40,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            sucursal_1_id = int(row[0])

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
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                )
                RETURNING id
                """,
                (
                    comercio_id,
                    f"C2{token}",
                    f"B2{token}",
                    f"S2{token}",
                    "Sucursal 2",
                    "Calle 2",
                    "Cordoba",
                    "X",
                    -31.42,
                    -64.12,
                    -64.12,
                    -31.42,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            sucursal_2_id = int(row[0])

            for idx, nombre in enumerate(("Leche", "Pan"), start=1):
                cur.execute(
                    """
                    INSERT INTO producto (codigo_ean, nombre)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (f"7790000{token[-6:]}{idx}"[-13:], nombre),
                )
                row = cur.fetchone()
                assert row is not None
                producto_id = int(row[0])
                producto_ids.append(producto_id)

                cur.execute(
                    """
                    INSERT INTO item_carrito (carrito_id, producto_id, cantidad)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (carrito_id, producto_id, 1),
                )
                row = cur.fetchone()
                assert row is not None

            precios = [
                (producto_ids[0], sucursal_1_id, 100.0),
                (producto_ids[0], sucursal_2_id, 200.0),
                (producto_ids[1], sucursal_1_id, 200.0),
                (producto_ids[1], sucursal_2_id, 100.0),
            ]
            for producto_id, sucursal_id, valor in precios:
                cur.execute(
                    """
                    INSERT INTO precio (producto_id, sucursal_id, valor, fecha_vigencia)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (producto_id, sucursal_id, valor, date.today()),
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
                    now,
                    200.0,
                    20.0,
                    10,
                    3,
                    "MENOR_PRECIO",
                    -31.4,
                    -64.1,
                    -64.1,
                    -31.4,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            distribucion_id = int(row[0])

            cur.execute(
                """
                INSERT INTO asignacion_sucursal (
                    carrito_distribuido_id,
                    sucursal_id,
                    subtotal
                ) VALUES (%s, %s, %s)
                RETURNING id
                """,
                (distribucion_id, sucursal_1_id, 100.0),
            )
            row = cur.fetchone()
            assert row is not None
            asignacion_1_id = int(row[0])

            cur.execute(
                """
                INSERT INTO asignacion_sucursal (
                    carrito_distribuido_id,
                    sucursal_id,
                    subtotal
                ) VALUES (%s, %s, %s)
                RETURNING id
                """,
                (distribucion_id, sucursal_2_id, 100.0),
            )
            row = cur.fetchone()
            assert row is not None
            asignacion_2_id = int(row[0])

            cur.execute(
                """
                INSERT INTO item_asignado (
                    asignacion_sucursal_id,
                    item_carrito_id,
                    precio_id,
                    cantidad,
                    precio_unitario,
                    subtotal
                ) VALUES (
                    %s,
                    (SELECT id FROM item_carrito WHERE carrito_id = %s AND producto_id = %s),
                    (SELECT id FROM precio WHERE producto_id = %s AND sucursal_id = %s),
                    1,
                    %s,
                    %s
                )
                """,
                (asignacion_1_id, carrito_id, producto_ids[0], producto_ids[0], sucursal_1_id, 100.0, 100.0),
            )
            cur.execute(
                """
                INSERT INTO item_asignado (
                    asignacion_sucursal_id,
                    item_carrito_id,
                    precio_id,
                    cantidad,
                    precio_unitario,
                    subtotal
                ) VALUES (
                    %s,
                    (SELECT id FROM item_carrito WHERE carrito_id = %s AND producto_id = %s),
                    (SELECT id FROM precio WHERE producto_id = %s AND sucursal_id = %s),
                    1,
                    %s,
                    %s
                )
                """,
                (asignacion_2_id, carrito_id, producto_ids[1], producto_ids[1], sucursal_2_id, 100.0, 100.0),
            )

            cur.execute(
                """
                INSERT INTO ruteo (carrito_distribuido_id, distancia_total_km)
                VALUES (%s, %s)
                RETURNING id
                """,
                (distribucion_id, 2.0),
            )
            row = cur.fetchone()
            assert row is not None
            ruteo_id = int(row[0])

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
                ) VALUES (%s, NULL, 0, 0.0, true, false, %s, %s)
                """,
                (ruteo_id, -31.4, -64.1),
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
                ) VALUES (%s, %s, 1, 1.0, false, false)
                """,
                (ruteo_id, sucursal_2_id),
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
                ) VALUES (%s, %s, 2, 1.0, false, false)
                """,
                (ruteo_id, sucursal_1_id),
            )

        conn.commit()

    try:
        _override_auth(usuario_id)
        response = client.get(f"/api/v1/carritos/{carrito_id}/distribucion")
        assert response.status_code == 200
        body = response.json()

        assert [asignacion["sucursal_id"] for asignacion in body["asignaciones"]] == [
            sucursal_2_id,
            sucursal_1_id,
        ]
        assert [parada["sucursal_id"] for parada in body["ruteo"]["paradas"]] == [
            None,
            sucursal_2_id,
            sucursal_1_id,
        ]
        assert body["ruteo"]["paradas"][1]["productos"] == ["Pan"]
        assert body["ruteo"]["paradas"][2]["productos"] == ["Leche"]
    finally:
        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM parada WHERE ruteo_id IN (SELECT id FROM ruteo WHERE carrito_distribuido_id IN (SELECT id FROM carrito_distribuido WHERE carrito_id = %s))", (carrito_id,))
                cur.execute("DELETE FROM ruteo WHERE carrito_distribuido_id IN (SELECT id FROM carrito_distribuido WHERE carrito_id = %s)", (carrito_id,))
                cur.execute("DELETE FROM item_asignado WHERE asignacion_sucursal_id IN (SELECT id FROM asignacion_sucursal WHERE carrito_distribuido_id IN (SELECT id FROM carrito_distribuido WHERE carrito_id = %s))", (carrito_id,))
                cur.execute("DELETE FROM asignacion_sucursal WHERE carrito_distribuido_id IN (SELECT id FROM carrito_distribuido WHERE carrito_id = %s)", (carrito_id,))
                cur.execute("DELETE FROM carrito_distribuido WHERE carrito_id = %s", (carrito_id,))
                cur.execute("DELETE FROM item_carrito WHERE carrito_id = %s", (carrito_id,))
                cur.execute("DELETE FROM precio WHERE producto_id = ANY(%s)", (list(producto_ids),))
                if comercio_id is not None:
                    cur.execute("DELETE FROM sucursal WHERE comercio_id = %s", (comercio_id,))
                    cur.execute("DELETE FROM comercio WHERE id = %s", (comercio_id,))
                cur.execute("DELETE FROM carrito WHERE id = %s", (carrito_id,))
                cur.execute("DELETE FROM usuario WHERE id = %s", (usuario_id,))
            conn.commit()


def test_distribuir_happy_path_cumple_sla_5s(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=True, item_count=10)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        start = perf_counter()
        response = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        elapsed = perf_counter() - start

        assert response.status_code == 200
        assert elapsed <= 5.0
    finally:
        _cleanup_seed(context)


def test_eliminar_carrito_tras_distribuir_ok(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=True, item_count=2)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        distribuir = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert distribuir.status_code == 200
        assert _count_distribuciones(context.carrito_id) == 1

        eliminar = client.delete(f"/api/v1/carritos/{context.carrito_id}")
        assert eliminar.status_code == 204
        assert _count_distribuciones(context.carrito_id) == 0

        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM carrito WHERE id = %s",
                    (context.carrito_id,),
                )
                assert cur.fetchone() is None
    finally:
        _cleanup_seed(context)


def test_eliminar_item_tras_distribuir_ok(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=True, item_count=2)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        distribuir = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert distribuir.status_code == 200
        assert _count_distribuciones(context.carrito_id) == 1

        item_ids = _item_carrito_ids(context.carrito_id)
        item_a_eliminar = item_ids[0]

        eliminar = client.delete(
            f"/api/v1/carritos/{context.carrito_id}/items/{item_a_eliminar}",
        )
        assert eliminar.status_code == 204
        assert _count_distribuciones(context.carrito_id) == 0

        ids_restantes = _item_carrito_ids(context.carrito_id)
        assert item_a_eliminar not in ids_restantes

        distribucion = client.get(f"/api/v1/carritos/{context.carrito_id}/distribucion")
        assert distribucion.status_code == 404
    finally:
        _cleanup_seed(context)


def test_modificar_item_invalida_distribucion(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=True, item_count=2)
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        first = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert first.status_code == 200

        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE precio SET valor = valor + 50 WHERE id = %s",
                    (context.precio_ids[0],),
                )
            conn.commit()

        second = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert second.status_code == 200
        assert _count_distribuciones(context.carrito_id) == 2

        item_id = _item_carrito_ids(context.carrito_id)[0]
        actualizar = client.patch(
            f"/api/v1/carritos/{context.carrito_id}/items/{item_id}",
            json={"cantidad": 2},
        )
        assert actualizar.status_code == 200
        assert _count_distribuciones(context.carrito_id) == 0

        distribucion = client.get(f"/api/v1/carritos/{context.carrito_id}/distribucion")
        assert distribucion.status_code == 404
    finally:
        _cleanup_seed(context)


def test_agregar_item_invalida_distribucion(client: TestClient) -> None:
    context = _seed_context(with_items=True, preferencias_validas=True, item_count=1)
    nuevo_producto_id: int | None = None
    try:
        _override_auth(context.usuario_id)
        _override_real_service()

        distribuir = client.post(f"/api/v1/carritos/{context.carrito_id}/distribuir")
        assert distribuir.status_code == 200
        assert _count_distribuciones(context.carrito_id) == 1

        with psycopg.connect(LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                codigo_ean = f"7790000{context.carrito_id:06d}99"[-13:]
                cur.execute(
                    """
                    INSERT INTO producto (codigo_ean, nombre)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (codigo_ean, "Producto extra invalidación"),
                )
                row = cur.fetchone()
                assert row is not None
                nuevo_producto_id = int(row[0])
            conn.commit()

        agregar = client.post(
            f"/api/v1/carritos/{context.carrito_id}/items",
            json={"producto_id": nuevo_producto_id, "cantidad": 1},
        )
        assert agregar.status_code == 201
        assert _count_distribuciones(context.carrito_id) == 0

        distribucion = client.get(f"/api/v1/carritos/{context.carrito_id}/distribucion")
        assert distribucion.status_code == 404
    finally:
        _cleanup_seed(context)
        if nuevo_producto_id is not None:
            with psycopg.connect(LOCAL_DB_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM producto WHERE id = %s", (nuevo_producto_id,))
                conn.commit()
