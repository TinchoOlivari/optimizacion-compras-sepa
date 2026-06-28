from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

EstadoItem = Literal["PENDIENTE", "CONSEGUIDO", "NO_ENCONTRADO", "DESCARTADO"]
EstadoItemActualizable = Literal["PENDIENTE", "CONSEGUIDO", "NO_ENCONTRADO", "DESCARTADO"]
EstadoItemTerminal = Literal["CONSEGUIDO", "NO_ENCONTRADO", "DESCARTADO"]
EstadoCierre = Literal["COMPLETADA", "INTERRUMPIDA"]


@dataclass(frozen=True)
class ItemCompraGuiada:
    progreso_item_id: int
    item_asignado_id: int
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    estado: EstadoItem
    url_imagen: str | None = None


@dataclass(frozen=True)
class ParadaCompraGuiada:
    orden: int
    sucursal_id: int
    sucursal: str
    comercio: str
    direccion: str | None
    localidad: str | None
    provincia: str | None
    distancia_desde_anterior_km: float
    bandera_nombre: str | None
    bandera_logo_url: str | None
    subtotal: float
    items: list[ItemCompraGuiada]


@dataclass(frozen=True)
class CompraGuiadaDetalle:
    id: int
    carrito_distribuido_id: int
    fecha_inicio: datetime
    fecha_cierre: datetime | None
    estado_cierre: EstadoCierre | None
    paradas: list[ParadaCompraGuiada]


class CompraGuiadaError(Exception):
    pass


class CompraGuiadaNotFoundError(CompraGuiadaError):
    pass


class CompraGuiadaValidationError(CompraGuiadaError):
    pass


class CompraGuiadaPendienteError(CompraGuiadaValidationError):
    pass


class ICompraGuiadaRepository(Protocol):
    def iniciar(self, usuario_id: int, carrito_distribuido_id: int) -> CompraGuiadaDetalle: ...

    def obtener(self, usuario_id: int, compra_id: int) -> CompraGuiadaDetalle | None: ...

    def actualizar_item(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        estado: EstadoItemActualizable,
    ) -> CompraGuiadaDetalle | None: ...

    def finalizar(
        self,
        usuario_id: int,
        compra_id: int,
        estado_cierre: EstadoCierre,
    ) -> CompraGuiadaDetalle | None: ...
