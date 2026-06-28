"""Tests de integración del SQL de catalogo_repo contra la base real.

Solo se ejecutan si hay una base de datos accesible. Sirven para cubrir el
camino del cursor.execute (no mockeado) y bloquear regresiones del tipo
IndeterminateDatatype que aparecen cuando psycopg envía None como NULL
sin OID de tipo.
"""


import psycopg
import pytest

from app.core.config import get_settings
from app.infra.catalogo_repo import CatalogoRepository

LOCAL_DB_URL = "postgresql://tfg:tfg@localhost:5432/tfg"


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> CatalogoRepository:
    monkeypatch.setenv("DATABASE_URL", LOCAL_DB_URL)
    get_settings.cache_clear()
    return CatalogoRepository()


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


def test_obtener_precios_sin_geo_devuelve_lista_vacia(
    repo: CatalogoRepository,
) -> None:
    """Sin lat/lon/radio_km no se consulta el catálogo nacional completo."""
    resultados = repo.obtener_precios_producto(
        1,
        lat=None,
        lon=None,
        radio_km=None,
    )

    assert resultados == []


def test_obtener_precios_con_geo_devuelve_comercios_unicos_ordenados_y_limitados(
    repo: CatalogoRepository,
) -> None:
    """Con lat/lon/radio_km devuelve hasta 6 comercios con el mejor precio por cadena."""
    resultados = repo.obtener_precios_producto(
        1,
        lat=-31.4,
        lon=-64.1,
        radio_km=50,
        limite=6,
    )

    assert len(resultados) <= 6
    comercio_ids = [r.comercio_id for r in resultados]
    assert len(comercio_ids) == len(set(comercio_ids))
    distancias = [r.distancia_km for r in resultados]
    assert all(distancia is not None and distancia >= 0 for distancia in distancias)
    assert distancias == sorted(distancias)
