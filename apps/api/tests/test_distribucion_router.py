from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_current_user
from app.api.v1.preferencias import get_distribucion_service
from app.domain.optimizacion import (
    ConfiguracionOptimizacion,
    DistribucionCarritoVacioError,
    DistribucionNoEncontradaError,
    ResultadoDistribucion,
    RuteoResultado,
)
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


def _override_auth() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }


class _FakeDistribucionService:
    def __init__(self) -> None:
        self.error_distribuir: Exception | None = None
        self.error_obtener: Exception | None = None

    def distribuir(self, usuario_id: int, carrito_id: int) -> ResultadoDistribucion:
        _ = (usuario_id, carrito_id)
        if self.error_distribuir is not None:
            raise self.error_distribuir
        return ResultadoDistribucion(
            fecha_calculo=datetime(2026, 1, 1, tzinfo=UTC),
            costo_total_estimado=100.0,
            ahorro_estimado=10.0,
            configuracion=ConfiguracionOptimizacion(
                radio_km=5,
                max_paradas=3,
                preferencia="MENOR_PRECIO",
                origen_lat=-31.4,
                origen_lon=-64.1,
                por_defecto_aplicado=("max_paradas",),
            ),
            asignaciones=[],
            items_no_asignados=[],
            ruteo=RuteoResultado(distancia_total_km=0.0, paradas=[]),
            id=9,
        )

    def obtener_distribucion_vigente(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> ResultadoDistribucion:
        _ = (usuario_id, carrito_id)
        if self.error_obtener is not None:
            raise self.error_obtener
        return self.distribuir(usuario_id, carrito_id)


def test_distribuir_carrito_200() -> None:
    fake = _FakeDistribucionService()
    _override_auth()
    app.dependency_overrides[get_distribucion_service] = lambda: fake

    response = client.post("/api/v1/carritos/5/distribuir")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 9
    assert body["costo_total_estimado"] == 100.0
    assert body["configuracion"]["por_defecto_aplicado"] == ["max_paradas"]


def test_distribuir_carrito_409_si_vacio() -> None:
    fake = _FakeDistribucionService()
    fake.error_distribuir = DistribucionCarritoVacioError("El carrito está vacío.")
    _override_auth()
    app.dependency_overrides[get_distribucion_service] = lambda: fake

    response = client.post("/api/v1/carritos/5/distribuir")

    assert response.status_code == 409


def test_obtener_distribucion_404() -> None:
    fake = _FakeDistribucionService()
    fake.error_obtener = DistribucionNoEncontradaError("No hay distribución")
    _override_auth()
    app.dependency_overrides[get_distribucion_service] = lambda: fake

    response = client.get("/api/v1/carritos/5/distribucion")

    assert response.status_code == 404
