from collections.abc import Iterator
from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.api.v1.compras_guiadas import get_compra_guiada_service
from app.api.v1.dependencies import get_current_user
from app.domain.compra_guiada import (
    CompraGuiadaDetalle,
    CompraGuiadaPendienteError,
    EstadoItem,
    EstadoItemTerminal,
    ItemCompraGuiada,
    ParadaCompraGuiada,
)
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


class _FakeCompraGuiadaService:
    def __init__(self) -> None:
        self.actualizado: tuple[int, int, int, EstadoItemTerminal] | None = None
        self.finalizar_error: Exception | None = None

    def iniciar(self, usuario_id: int, carrito_distribuido_id: int) -> CompraGuiadaDetalle:
        _ = (usuario_id, carrito_distribuido_id)
        return _compra()

    def obtener(self, usuario_id: int, compra_id: int) -> CompraGuiadaDetalle:
        _ = (usuario_id, compra_id)
        return _compra()

    def actualizar_item(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        estado: EstadoItemTerminal,
    ) -> CompraGuiadaDetalle:
        self.actualizado = (usuario_id, compra_id, progreso_item_id, estado)
        return _compra(estado=estado)

    def finalizar(
        self,
        usuario_id: int,
        compra_id: int,
        *,
        confirmar_interrupcion: bool = False,
    ) -> CompraGuiadaDetalle:
        _ = (usuario_id, compra_id, confirmar_interrupcion)
        if self.finalizar_error is not None:
            raise self.finalizar_error
        return _compra(estado="CONSEGUIDO")


def _override_auth() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }


def test_iniciar_compra_guiada_201() -> None:
    _override_auth()
    app.dependency_overrides[get_compra_guiada_service] = lambda: _FakeCompraGuiadaService()

    response = client.post("/api/v1/compras-guiadas", json={"carrito_distribuido_id": 9})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 2
    assert body["paradas"][0]["items"][0]["estado"] == "PENDIENTE"


def test_actualizar_no_encontrado_no_devuelve_alternativas() -> None:
    fake = _FakeCompraGuiadaService()
    _override_auth()
    app.dependency_overrides[get_compra_guiada_service] = lambda: fake

    response = client.patch(
        "/api/v1/compras-guiadas/2/items/3",
        json={"estado": "NO_ENCONTRADO"},
    )

    assert response.status_code == 200
    assert fake.actualizado == (1, 2, 3, "NO_ENCONTRADO")
    body = response.json()
    assert body["paradas"][0]["items"][0]["estado"] == "NO_ENCONTRADO"
    assert "alternativas" not in body


def test_actualizar_rechaza_pendiente_por_contrato() -> None:
    _override_auth()
    app.dependency_overrides[get_compra_guiada_service] = lambda: _FakeCompraGuiadaService()

    response = client.patch(
        "/api/v1/compras-guiadas/2/items/3",
        json={"estado": "PENDIENTE"},
    )

    assert response.status_code == 422


def test_finalizar_409_si_hay_pendientes_sin_confirmacion() -> None:
    fake = _FakeCompraGuiadaService()
    fake.finalizar_error = CompraGuiadaPendienteError("Hay pendientes")
    _override_auth()
    app.dependency_overrides[get_compra_guiada_service] = lambda: fake

    response = client.post("/api/v1/compras-guiadas/2/finalizar", json={})

    assert response.status_code == 409


def _compra(estado: str = "PENDIENTE") -> CompraGuiadaDetalle:
    return CompraGuiadaDetalle(
        id=2,
        carrito_distribuido_id=9,
        fecha_inicio=datetime(2026, 1, 1, tzinfo=UTC),
        fecha_cierre=None,
        estado_cierre=None,
        paradas=[
            ParadaCompraGuiada(
                orden=1,
                sucursal_id=10,
                sucursal="Sucursal Centro",
                comercio="Comercio",
                direccion="Av. Siempre Viva 123",
                localidad="Córdoba",
                provincia="X",
                distancia_desde_anterior_km=1.2,
                bandera_nombre=None,
                bandera_logo_url=None,
                subtotal=100.0,
                items=[
                    ItemCompraGuiada(
                        progreso_item_id=3,
                        item_asignado_id=4,
                        item_carrito_id=5,
                        producto_id=6,
                        nombre_producto="Leche",
                        cantidad=1,
                        precio_unitario=100.0,
                        subtotal=100.0,
                        estado=cast(EstadoItem, estado),
                    )
                ],
            )
        ],
    )
