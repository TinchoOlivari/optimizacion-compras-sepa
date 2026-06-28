from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.domain.carrito import CarritoNotFoundError, CarritoService, CarritoValidationError
from app.domain.ports import Carrito, EliminacionCarrito, ItemCarrito


@dataclass
class FakeCarritoRepo:
    def __post_init__(self) -> None:
        self.carrito: Carrito | None = Carrito(
            id=5,
            usuario_id=1,
            titulo=None,
            activo=True,
            fecha_ultima_edicion=datetime(2026, 1, 1, tzinfo=UTC),
            cantidad_items=1,
        )
        self.item = ItemCarrito(id=20, carrito_id=5, producto_id=10, cantidad=4)
        self.promovio = False

    def listar_carritos(self, usuario_id: int) -> list[Carrito]:
        if self.carrito is None or usuario_id != self.carrito.usuario_id:
            return []
        return [self.carrito]

    def crear_carrito_activo(self, usuario_id: int, titulo: str | None = None) -> Carrito:
        self.carrito = Carrito(
            id=6,
            usuario_id=usuario_id,
            titulo=titulo,
            activo=True,
            fecha_ultima_edicion=datetime(2026, 1, 2, tzinfo=UTC),
            cantidad_items=0,
        )
        return self.carrito

    def obtener_carrito(self, usuario_id: int, carrito_id: int) -> Carrito | None:
        if (
            self.carrito is not None
            and usuario_id == self.carrito.usuario_id
            and carrito_id == self.carrito.id
        ):
            return self.carrito
        return None

    def actualizar_titulo(
        self,
        usuario_id: int,
        carrito_id: int,
        titulo: str | None,
    ) -> Carrito | None:
        if (
            self.carrito is None
            or usuario_id != self.carrito.usuario_id
            or carrito_id != self.carrito.id
        ):
            return None
        self.carrito = Carrito(
            id=self.carrito.id,
            usuario_id=self.carrito.usuario_id,
            titulo=titulo,
            activo=self.carrito.activo,
            fecha_ultima_edicion=self.carrito.fecha_ultima_edicion,
            cantidad_items=self.carrito.cantidad_items,
        )
        return self.carrito

    def activar_carrito(self, usuario_id: int, carrito_id: int) -> Carrito | None:
        if (
            self.carrito is None
            or usuario_id != self.carrito.usuario_id
            or carrito_id != self.carrito.id
        ):
            return None
        return self.carrito

    def eliminar_carrito(self, usuario_id: int, carrito_id: int) -> EliminacionCarrito:
        if (
            self.carrito is None
            or usuario_id != self.carrito.usuario_id
            or carrito_id != self.carrito.id
        ):
            return EliminacionCarrito(eliminado=False, era_activo=False)
        era_activo = self.carrito.activo
        self.carrito = None
        return EliminacionCarrito(eliminado=True, era_activo=era_activo)

    def promover_activo_o_crear(self, usuario_id: int) -> Carrito:
        self.promovio = True
        if self.carrito is None:
            raise RuntimeError("No hay carritos para promover")
        return self.carrito

    def obtener_item_por_producto(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
    ) -> ItemCarrito | None:
        if (
            self.carrito is not None
            and usuario_id == self.carrito.usuario_id
            and carrito_id == self.item.carrito_id
            and producto_id == self.item.producto_id
        ):
            return self.item
        return None

    def agregar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
        cantidad: int,
    ) -> ItemCarrito:
        self.item = ItemCarrito(
            id=self.item.id,
            carrito_id=carrito_id,
            producto_id=producto_id,
            cantidad=self.item.cantidad + cantidad,
        )
        return self.item

    def actualizar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        item_id: int,
        cantidad: int,
    ) -> ItemCarrito | None:
        if item_id != self.item.id or carrito_id != self.item.carrito_id:
            return None
        self.item = ItemCarrito(
            id=self.item.id,
            carrito_id=self.item.carrito_id,
            producto_id=self.item.producto_id,
            cantidad=cantidad,
        )
        return self.item

    def eliminar_item(self, usuario_id: int, carrito_id: int, item_id: int) -> bool:
        return item_id == self.item.id and carrito_id == self.item.carrito_id


def test_agregar_item_suma_cantidad() -> None:
    service = CarritoService(FakeCarritoRepo())

    result = service.agregar_item(usuario_id=1, carrito_id=5, producto_id=10, cantidad=3)

    assert result.cantidad == 7


def test_agregar_item_excediendo_99_falla() -> None:
    repo = FakeCarritoRepo()
    repo.item = ItemCarrito(id=20, carrito_id=5, producto_id=10, cantidad=97)
    service = CarritoService(repo)

    with pytest.raises(CarritoValidationError):
        service.agregar_item(usuario_id=1, carrito_id=5, producto_id=10, cantidad=5)


def test_editar_item_cantidad_invalida_falla() -> None:
    service = CarritoService(FakeCarritoRepo())

    with pytest.raises(CarritoValidationError):
        service.editar_item(usuario_id=1, carrito_id=5, item_id=20, cantidad=0)


def test_listar_sin_carritos_devuelve_lista_vacia() -> None:
    repo = FakeCarritoRepo()
    repo.carrito = Carrito(
        id=5,
        usuario_id=99,
        titulo=None,
        activo=True,
        fecha_ultima_edicion=datetime(2026, 1, 1, tzinfo=UTC),
        cantidad_items=0,
    )
    service = CarritoService(repo)

    assert service.listar(usuario_id=1) == []


def test_obtener_activo_detalle_sin_activo_falla() -> None:
    repo = FakeCarritoRepo()
    repo.carrito = Carrito(
        id=5,
        usuario_id=1,
        titulo="Guardado",
        activo=False,
        fecha_ultima_edicion=datetime(2026, 1, 1, tzinfo=UTC),
        cantidad_items=0,
    )
    service = CarritoService(repo)

    with pytest.raises(CarritoNotFoundError):
        service.obtener_activo_detalle(usuario_id=1)


def test_eliminar_carrito_activo_promueve_otro() -> None:
    repo = FakeCarritoRepo()
    service = CarritoService(repo)

    result = service.eliminar(usuario_id=1, carrito_id=5)

    assert result.eliminado is True
    assert repo.promovio is True


def test_eliminar_ultimo_carrito_activo_no_crea_reemplazo() -> None:
    repo = FakeCarritoRepo()
    service = CarritoService(repo)

    result = service.eliminar(usuario_id=1, carrito_id=5)

    assert result.eliminado is True
    assert repo.promovio is True
    assert repo.carrito is None
    assert service.listar(usuario_id=1) == []


def test_renombrar_carrito_inexistente_falla() -> None:
    service = CarritoService(FakeCarritoRepo())

    with pytest.raises(CarritoNotFoundError):
        service.renombrar(usuario_id=1, carrito_id=999, titulo="Semanal")
