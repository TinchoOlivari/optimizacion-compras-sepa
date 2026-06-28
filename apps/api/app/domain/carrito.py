from dataclasses import dataclass

from app.domain.ports import (
    Carrito,
    EliminacionCarrito,
    ICarritoRepository,
    ItemCarrito,
    ProductoResumen,
)


class CarritoError(Exception):
    pass


class CarritoNotFoundError(CarritoError):
    pass


class CarritoForbiddenError(CarritoError):
    pass


class CarritoValidationError(CarritoError):
    pass


@dataclass(frozen=True)
class ResultadoAgregarItem:
    item: ItemCarrito
    creado: bool


class CarritoService:
    def __init__(self, carrito_repo: ICarritoRepository) -> None:
        self._carrito_repo = carrito_repo

    def listar(self, usuario_id: int) -> list[Carrito]:
        return self._carrito_repo.listar_carritos(usuario_id)

    def crear(self, usuario_id: int) -> Carrito:
        return self._carrito_repo.crear_carrito_activo(usuario_id)

    def obtener(self, usuario_id: int, carrito_id: int) -> Carrito:
        carrito = self._carrito_repo.obtener_carrito(usuario_id, carrito_id)
        if carrito is None:
            raise CarritoNotFoundError("Carrito no encontrado")
        return carrito

    def obtener_activo_detalle(
        self,
        usuario_id: int,
    ) -> tuple[Carrito, list[tuple[ItemCarrito, ProductoResumen | None]]]:
        carritos = self._carrito_repo.listar_carritos(usuario_id)
        carrito_activo = next((c for c in carritos if c.activo), None)
        if carrito_activo is None:
            raise CarritoNotFoundError("No tenés un carrito activo")

        items = self._carrito_repo.listar_items_con_producto(usuario_id, carrito_activo.id)
        return carrito_activo, items

    def renombrar(self, usuario_id: int, carrito_id: int, titulo: str | None) -> Carrito:
        carrito = self._carrito_repo.actualizar_titulo(usuario_id, carrito_id, titulo)
        if carrito is None:
            raise CarritoNotFoundError("Carrito no encontrado")
        return carrito

    def activar(self, usuario_id: int, carrito_id: int) -> Carrito:
        carrito = self._carrito_repo.activar_carrito(usuario_id, carrito_id)
        if carrito is None:
            raise CarritoForbiddenError("No tenés permisos sobre ese carrito")
        return carrito

    def eliminar(self, usuario_id: int, carrito_id: int) -> EliminacionCarrito:
        resultado = self._carrito_repo.eliminar_carrito(usuario_id, carrito_id)
        if not resultado.eliminado:
            raise CarritoNotFoundError("Carrito no encontrado")
        if resultado.era_activo:
            try:
                self._carrito_repo.promover_activo_o_crear(usuario_id)
            except RuntimeError:
                pass
        return resultado

    def agregar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
        cantidad: int,
    ) -> ItemCarrito:
        return self.agregar_item_detallado(
            usuario_id=usuario_id,
            carrito_id=carrito_id,
            producto_id=producto_id,
            cantidad=cantidad,
        ).item

    def agregar_item_detallado(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
        cantidad: int,
    ) -> ResultadoAgregarItem:
        self._validar_cantidad(cantidad)

        item_existente = self._carrito_repo.obtener_item_por_producto(
            usuario_id,
            carrito_id,
            producto_id,
        )
        if item_existente is not None and item_existente.cantidad + cantidad > 99:
            raise CarritoValidationError("La cantidad máxima por ítem es 99")

        try:
            item = self._carrito_repo.agregar_item(usuario_id, carrito_id, producto_id, cantidad)
        except RuntimeError as error:
            mensaje = str(error)
            if "permisos" in mensaje:
                raise CarritoForbiddenError("No tenés permisos sobre ese carrito") from error
            if "Producto" in mensaje:
                raise CarritoNotFoundError("Producto no encontrado") from error
            raise

        if item.carrito_id != carrito_id:
            raise CarritoForbiddenError("No tenés permisos sobre ese carrito")
        return ResultadoAgregarItem(item=item, creado=item_existente is None)

    def editar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        item_id: int,
        cantidad: int,
    ) -> ItemCarrito:
        self._validar_cantidad(cantidad)

        try:
            item = self._carrito_repo.actualizar_item(usuario_id, carrito_id, item_id, cantidad)
        except RuntimeError as error:
            mensaje = str(error)
            if "permisos" in mensaje:
                raise CarritoForbiddenError("No tenés permisos sobre ese carrito") from error
            raise

        if item is None:
            raise CarritoNotFoundError("Ítem no encontrado")
        return item

    def eliminar_item(self, usuario_id: int, carrito_id: int, item_id: int) -> None:
        try:
            eliminado = self._carrito_repo.eliminar_item(usuario_id, carrito_id, item_id)
        except RuntimeError as error:
            mensaje = str(error)
            if "permisos" in mensaje:
                raise CarritoForbiddenError("No tenés permisos sobre ese carrito") from error
            raise

        if not eliminado:
            raise CarritoNotFoundError("Ítem no encontrado")

    @staticmethod
    def _validar_cantidad(cantidad: int) -> None:
        if cantidad < 1 or cantidad > 99:
            raise CarritoValidationError("La cantidad debe estar entre 1 y 99")
