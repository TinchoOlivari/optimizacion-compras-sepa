from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.productos import get_catalogo_service
from app.domain.catalogo import (
    CatalogoNotFoundError,
    CatalogoValidationError,
    DetalleProductoResultado,
    PrecioProductoResultado,
)
from app.domain.ports import ProductoResumen
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


def _producto() -> ProductoResumen:
    return ProductoResumen(
        id=42,
        codigo_ean="7790580492432",
        nombre="Leche Entera",
        marca="Marca",
        presentacion="1L",
        url_imagen="https://img.test/leche.png",
    )


class _FakeCatalogoService:
    def __init__(self) -> None:
        self.buscar_result: list[ProductoResumen] = [_producto()]
        self.detalle_result = DetalleProductoResultado(
            producto=_producto(),
            precios=[
                PrecioProductoResultado(
                    comercio_id=1,
                    comercio="Comercio Uno",
                    sucursal_id=10,
                    sucursal="Sucursal Centro",
                    direccion="Calle 123",
                    localidad="Córdoba",
                    provincia="Córdoba",
                    precio=850.0,
                    fecha_vigencia=datetime(2026, 1, 1, tzinfo=UTC).date().isoformat(),
                    distancia_km=None,
                    precio_minimo=True,
                )
            ],
            filtro_radio_activo=False,
            mensaje="Indicá tu ubicación para ver precios cercanos",
        )
        self.buscar_error: Exception | None = None
        self.detalle_error: Exception | None = None

    def buscar(self, q: str, limite: int = 5) -> list[ProductoResumen]:
        _ = (q, limite)
        if self.buscar_error is not None:
            raise self.buscar_error
        return self.buscar_result

    def detalle(
        self,
        producto_id: int,
        *,
        lat: float | None = None,
        lon: float | None = None,
        radio_km: int | None = None,
    ) -> DetalleProductoResultado:
        _ = (producto_id, lat, lon, radio_km)
        if self.detalle_error is not None:
            raise self.detalle_error
        return self.detalle_result


def test_buscar_productos_200() -> None:
    fake = _FakeCatalogoService()
    app.dependency_overrides[get_catalogo_service] = lambda: fake

    response = client.get("/api/v1/productos/buscar", params={"q": "lech"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["codigo_ean"] == "7790580492432"


def test_buscar_productos_422_param_invalido() -> None:
    fake = _FakeCatalogoService()
    fake.buscar_error = CatalogoValidationError(
        "La búsqueda por nombre requiere al menos 4 caracteres"
    )
    app.dependency_overrides[get_catalogo_service] = lambda: fake

    response = client.get("/api/v1/productos/buscar", params={"q": "le"})

    assert response.status_code == 422
    error = response.json()["detail"]["error"]
    assert error["codigo"] == "PARAM_INVALIDO"
    assert error["campos"] == ["q"]


def test_detalle_producto_200_sin_radio() -> None:
    fake = _FakeCatalogoService()
    app.dependency_overrides[get_catalogo_service] = lambda: fake

    response = client.get("/api/v1/productos/42")

    assert response.status_code == 200
    body = response.json()
    assert body["producto"]["id"] == 42
    assert body["filtro_radio_activo"] is False
    assert body["mensaje"] == "Indicá tu ubicación para ver precios cercanos"


def test_detalle_producto_422_si_radio_parcial() -> None:
    fake = _FakeCatalogoService()
    app.dependency_overrides[get_catalogo_service] = lambda: fake

    response = client.get("/api/v1/productos/42", params={"lat": -31.4})

    assert response.status_code == 422
    error = response.json()["detail"]["error"]
    assert error["codigo"] == "PARAM_INVALIDO"


def test_detalle_producto_404_si_no_existe() -> None:
    fake = _FakeCatalogoService()
    fake.detalle_error = CatalogoNotFoundError("Producto no encontrado")
    app.dependency_overrides[get_catalogo_service] = lambda: fake

    response = client.get("/api/v1/productos/9999")

    assert response.status_code == 404
    error = response.json()["detail"]["error"]
    assert error["codigo"] == "NO_ENCONTRADO"
