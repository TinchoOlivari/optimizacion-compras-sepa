from datetime import date
from decimal import Decimal

import psycopg
import pytest

from ingesta.parser import ComercioCSV, ProductoCSV, SucursalCSV
from ingesta.repository import RepositorioSEPA, _validate_sucursal_copy_row


@pytest.mark.integration
def test_repository_upsert_idempotente() -> None:
    import os

    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL o TEST_DATABASE_URL no está definido")

    try:
        with psycopg.connect(database_url) as conn:
            repo = RepositorioSEPA(conn)

            comercio = ComercioCSV(
                id_comercio="99998",
                id_bandera="1",
                cuit="30999999998",
                razon_social="COMERCIO TEST IDEMPOTENCIA",
                bandera_nombre="TEST",
            )
            ids_comercio = repo.upsert_comercios([comercio])
            map_comercio = {comercio.id_comercio: ids_comercio[comercio.cuit]}

            bandera_ids = repo.upsert_banderas([comercio])

            sucursal = SucursalCSV(
                id_comercio="99998",
                id_bandera="1",
                id_sucursal="1",
                nombre="Sucursal Test",
                direccion="Calle 123",
                localidad="Cordoba",
                provincia="Buenos Aires",
                latitud=-31.0,
                longitud=-64.0,
            )
            ids_sucursal = repo.upsert_sucursales([sucursal], map_comercio, bandera_ids)
            ids_sucursal_reproceso = repo.upsert_sucursales([sucursal], map_comercio, bandera_ids)
            assert ids_sucursal_reproceso == ids_sucursal

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM sucursal
                    WHERE sepa_id_comercio = %s
                      AND sepa_id_bandera = %s
                      AND sepa_id_sucursal = %s
                    """,
                    (sucursal.id_comercio, sucursal.id_bandera, sucursal.id_sucursal),
                )
                count_sucursal = cur.fetchone()
                assert count_sucursal is not None
                assert int(count_sucursal[0]) == 1

            producto = ProductoCSV(
                id_comercio="99998",
                id_bandera="1",
                id_sucursal="1",
                codigo_ean="7790742363008",
                productos_ean="1",
                descripcion="Leche Test",
                cantidad_presentacion="1",
                unidad_medida_presentacion="ltr",
                marca="TEST",
                precio_lista=Decimal("1234.56"),
            )
            ids_producto = repo.upsert_productos([producto])

            fecha_vigencia = date(2026, 4, 14)
            repo.upsert_precios([producto], ids_producto, ids_sucursal, fecha_vigencia)
            repo.upsert_precios([producto], ids_producto, ids_sucursal, fecha_vigencia)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM precio p
                    JOIN producto pr ON pr.id = p.producto_id
                    JOIN sucursal s ON s.id = p.sucursal_id
                    WHERE pr.codigo_ean = %s
                      AND s.sepa_id_comercio = %s
                      AND s.sepa_id_bandera = %s
                      AND s.sepa_id_sucursal = %s
                      AND p.fecha_vigencia = %s
                    """,
                    (producto.codigo_ean, "99998", "1", "1", fecha_vigencia),
                )
                count = cur.fetchone()
                assert count is not None
                assert int(count[0]) == 1

            conn.rollback()
    except psycopg.OperationalError:
        pytest.skip("No fue posible conectar a PostgreSQL para test de integración")


def test_validate_sucursal_copy_row_rechaza_overflow() -> None:
    with pytest.raises(ValueError, match="id_comercio excede"):
        _validate_sucursal_copy_row(
            id_comercio="1" * 21,
            id_bandera="1",
            id_sucursal="1",
            provincia="Buenos Aires",
        )

    with pytest.raises(ValueError, match="provincia excede"):
        _validate_sucursal_copy_row(
            id_comercio="123",
            id_bandera="1",
            id_sucursal="1",
            provincia="P" * 65,
        )
