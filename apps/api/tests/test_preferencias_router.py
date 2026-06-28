from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_current_user
from app.api.v1.preferencias import get_distribucion_service
from app.domain.optimizacion import ConfiguracionOptimizacion
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


class _FakeDistribucionService:
    def obtener_preferencias(self, usuario_id: int) -> ConfiguracionOptimizacion:
        _ = usuario_id
        return ConfiguracionOptimizacion(
            radio_km=10,
            max_paradas=3,
            preferencia="MENOR_PRECIO",
            origen_lat=-31.4,
            origen_lon=-64.1,
            por_defecto_aplicado=("max_paradas",),
            origen_direccion="Av. Colón 4747",
            origen_modalidad="PUNTO_EN_MAPA",
        )

    def guardar_preferencias(self, usuario_id: int, **kwargs: object) -> ConfiguracionOptimizacion:
        _ = (usuario_id, kwargs)
        return self.obtener_preferencias(usuario_id)


def _override_auth() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }


def test_get_preferencias_200() -> None:
    _override_auth()
    app.dependency_overrides[get_distribucion_service] = lambda: _FakeDistribucionService()

    response = client.get("/api/v1/preferencias")

    assert response.status_code == 200
    assert response.json()["radio_km"] == 10
    assert response.json()["origen"]["direccion"] == "Av. Colón 4747"
    assert response.json()["origen"]["modalidad"] == "PUNTO_EN_MAPA"


def test_put_preferencias_200() -> None:
    _override_auth()
    app.dependency_overrides[get_distribucion_service] = lambda: _FakeDistribucionService()

    response = client.put(
        "/api/v1/preferencias",
        json={
            "radio_km": 12,
            "ubicacion_referencia": {"latitud": -31.4, "longitud": -64.1},
        },
    )

    assert response.status_code == 200
    assert response.json()["preferencia"] == "MENOR_PRECIO"
