from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.carritos import get_carrito_service
from app.api.v1.dependencies import get_current_user
from app.domain.carrito import (
    CarritoForbiddenError,
    CarritoNotFoundError,
    CarritoValidationError,
    ResultadoAgregarItem,
)
from app.domain.ports import Carrito, EliminacionCarrito, ItemCarrito, ProductoResumen
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


def _carrito_base() -> Carrito:
    return Carrito(
        id=5,
        usuario_id=1,
        titulo="Compras semana",
        activo=True,
        fecha_ultima_edicion=datetime(2026, 1, 1, tzinfo=UTC),
        cantidad_items=1,
    )


class _FakeCarritoService:
    def __init__(self) -> None:
        self.carrito = _carrito_base()
        self.item = ItemCarrito(id=20, carrito_id=5, producto_id=10, cantidad=3)

        self.listar_result: list[Carrito] = [self.carrito]
        self.crear_result: Carrito = Carrito(
            id=6,
            usuario_id=1,
            titulo=None,
            activo=True,
            fecha_ultima_edicion=datetime(2026, 1, 2, tzinfo=UTC),
            cantidad_items=0,
        )
        self.obtener_result: Carrito = self.carrito
        self.agregar_result = ResultadoAgregarItem(item=self.item, creado=True)
        self.obtener_activo_detalle_error: Exception | None = None
        self.obtener_activo_detalle_result: tuple[
            Carrito,
            list[tuple[ItemCarrito, ProductoResumen | None]],
        ] = (
            self.carrito,
            [(self.item, None)],
        )

        self.activar_error: Exception | None = None
        self.renombrar_error: Exception | None = None
        self.obtener_error: Exception | None = None
        self.eliminar_error: Exception | None = None
        self.agregar_error: Exception | None = None
        self.editar_error: Exception | None = None
        self.eliminar_item_error: Exception | None = None

    def listar(self, usuario_id: int) -> list[Carrito]:
        _ = usuario_id
        return self.listar_result

    def crear(self, usuario_id: int) -> Carrito:
        _ = usuario_id
        return self.crear_result

    def obtener(self, usuario_id: int, carrito_id: int) -> Carrito:
        _ = (usuario_id, carrito_id)
        if self.obtener_error is not None:
            raise self.obtener_error
        return self.obtener_result

    def obtener_activo_detalle(
        self,
        usuario_id: int,
    ) -> tuple[Carrito, list[tuple[ItemCarrito, ProductoResumen | None]]]:
        _ = usuario_id
        if self.obtener_activo_detalle_error is not None:
            raise self.obtener_activo_detalle_error
        return self.obtener_activo_detalle_result

    def activar(self, usuario_id: int, carrito_id: int) -> Carrito:
        _ = (usuario_id, carrito_id)
        if self.activar_error is not None:
            raise self.activar_error
        return self.carrito

    def renombrar(self, usuario_id: int, carrito_id: int, titulo: str | None) -> Carrito:
        _ = (usuario_id, carrito_id, titulo)
        if self.renombrar_error is not None:
            raise self.renombrar_error
        return self.carrito

    def eliminar(self, usuario_id: int, carrito_id: int) -> EliminacionCarrito:
        _ = (usuario_id, carrito_id)
        if self.eliminar_error is not None:
            raise self.eliminar_error
        return EliminacionCarrito(eliminado=True, era_activo=False)

    def agregar_item_detallado(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
        cantidad: int,
    ) -> ResultadoAgregarItem:
        _ = (usuario_id, carrito_id, producto_id, cantidad)
        if self.agregar_error is not None:
            raise self.agregar_error
        return self.agregar_result

    def editar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        item_id: int,
        cantidad: int,
    ) -> ItemCarrito:
        _ = (usuario_id, carrito_id, item_id, cantidad)
        if self.editar_error is not None:
            raise self.editar_error
        return self.item

    def eliminar_item(self, usuario_id: int, carrito_id: int, item_id: int) -> None:
        _ = (usuario_id, carrito_id, item_id)
        if self.eliminar_item_error is not None:
            raise self.eliminar_item_error


def _override_auth() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }


def test_listar_carritos_401_sin_auth() -> None:
    response = client.get("/api/v1/carritos")
    assert response.status_code == 401


def test_listar_carritos_200() -> None:
    fake = _FakeCarritoService()
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.get("/api/v1/carritos")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == 5


def test_listar_carritos_200_vacio() -> None:
    fake = _FakeCarritoService()
    fake.listar_result = []
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.get("/api/v1/carritos")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_crear_carrito_201() -> None:
    fake = _FakeCarritoService()
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.post("/api/v1/carritos")

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 6
    assert body["activo"] is True
    assert body["items"] == []


def test_obtener_carrito_404() -> None:
    fake = _FakeCarritoService()
    fake.obtener_error = CarritoNotFoundError("Carrito no encontrado")
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.get("/api/v1/carritos/99")

    assert response.status_code == 404


def test_patch_carrito_activo_403_otro_usuario() -> None:
    fake = _FakeCarritoService()
    fake.activar_error = CarritoForbiddenError("No tenés permisos sobre ese carrito")
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.patch("/api/v1/carritos/99", json={"activo": True})

    assert response.status_code == 403
    assert response.json()["detail"]["error"]["codigo"] == "SIN_PERMISOS"


def test_patch_carrito_titulo_200() -> None:
    fake = _FakeCarritoService()
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.patch("/api/v1/carritos/5", json={"titulo": "Compras finde"})

    assert response.status_code == 200
    assert response.json()["id"] == 5


def test_delete_carrito_204() -> None:
    fake = _FakeCarritoService()
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.delete("/api/v1/carritos/5")

    assert response.status_code == 204
    assert response.text == ""


def test_delete_carrito_404() -> None:
    fake = _FakeCarritoService()
    fake.eliminar_error = CarritoNotFoundError("Carrito no encontrado")
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.delete("/api/v1/carritos/9")

    assert response.status_code == 404


def test_post_item_201_cuando_es_nuevo() -> None:
    fake = _FakeCarritoService()
    fake.agregar_result = ResultadoAgregarItem(item=fake.item, creado=True)
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.post("/api/v1/carritos/5/items", json={"producto_id": 10, "cantidad": 3})

    assert response.status_code == 201
    assert response.json()["cantidad"] == 3


def test_post_item_200_cuando_ya_existia() -> None:
    fake = _FakeCarritoService()
    fake.agregar_result = ResultadoAgregarItem(
        item=ItemCarrito(id=20, carrito_id=5, producto_id=10, cantidad=7),
        creado=False,
    )
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.post("/api/v1/carritos/5/items", json={"producto_id": 10, "cantidad": 3})

    assert response.status_code == 200
    assert response.json()["cantidad"] == 7


def test_post_item_422_por_cantidad_maxima() -> None:
    fake = _FakeCarritoService()
    fake.agregar_error = CarritoValidationError("La cantidad máxima por ítem es 99")
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.post("/api/v1/carritos/5/items", json={"producto_id": 10, "cantidad": 5})

    assert response.status_code == 422
    assert response.json()["detail"]["error"]["codigo"] == "PARAM_INVALIDO"


def test_patch_item_200() -> None:
    fake = _FakeCarritoService()
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.patch("/api/v1/carritos/5/items/20", json={"cantidad": 8})

    assert response.status_code == 200
    assert response.json()["id"] == 20


def test_delete_item_403() -> None:
    fake = _FakeCarritoService()
    fake.eliminar_item_error = CarritoForbiddenError("No tenés permisos sobre ese carrito")
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.delete("/api/v1/carritos/5/items/20")

    assert response.status_code == 403


def test_delete_item_204() -> None:
    fake = _FakeCarritoService()
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.delete("/api/v1/carritos/5/items/20")

    assert response.status_code == 204


def test_obtener_carrito_activo_200_con_item_y_producto() -> None:
    fake = _FakeCarritoService()
    producto = ProductoResumen(
        id=10,
        codigo_ean="779000000001",
        nombre="Leche",
        marca="La Serenísima",
        presentacion="1 L",
        url_imagen=None,
    )
    fake.obtener_activo_detalle_result = (
        Carrito(
            id=7,
            usuario_id=1,
            titulo="Compras",
            activo=True,
            fecha_ultima_edicion=datetime(2026, 1, 3, tzinfo=UTC),
            cantidad_items=2,
        ),
        [(ItemCarrito(id=30, carrito_id=7, producto_id=10, cantidad=2), producto)],
    )
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.get("/api/v1/carritos/activo")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 7
    assert body["titulo"] == "Compras"
    assert body["activo"] is True
    assert "carrito" not in body
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == 30
    assert body["items"][0]["cantidad"] == 2
    assert body["items"][0]["producto"]["nombre"] == "Leche"


def test_obtener_carrito_activo_404_sin_activo() -> None:
    fake = _FakeCarritoService()
    fake.obtener_activo_detalle_error = CarritoNotFoundError("No tenés un carrito activo")
    _override_auth()
    app.dependency_overrides[get_carrito_service] = lambda: fake

    response = client.get("/api/v1/carritos/activo")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["codigo"] == "NO_ENCONTRADO"
