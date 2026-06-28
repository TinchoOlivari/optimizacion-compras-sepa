from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class UsuarioAuth:
    id: int
    nombre: str
    correo: str
    password_hash: str


@dataclass(frozen=True)
class ItemCarritoAnonimo:
    producto_id: int
    cantidad: int


@dataclass(frozen=True)
class TokenRecuperacion:
    usuario_id: int
    expira_en: datetime
    usado: bool


class IAuthRepository(Protocol):
    def crear_usuario(self, nombre: str, correo: str, password_hash: str) -> int: ...

    def obtener_por_correo(self, correo: str) -> UsuarioAuth | None: ...

    def obtener_por_id(self, usuario_id: int) -> UsuarioAuth | None: ...

    def actualizar_password(self, usuario_id: int, password_hash: str) -> None: ...

    def convertir_carrito_anonimo(
        self,
        usuario_id: int,
        items: list[ItemCarritoAnonimo],
    ) -> None: ...

    def activar_ultimo_carrito(self, usuario_id: int) -> None: ...

    def actualizar_nombre(self, usuario_id: int, nombre: str) -> None: ...


class ITokenRepository(Protocol):
    def guardar_hash(self, usuario_id: int, token_hash: str, expira_en: datetime) -> None: ...

    def validar(self, token_hash: str) -> TokenRecuperacion | None: ...

    def marcar_usado(self, token_hash: str) -> None: ...


class IEmailSender(Protocol):
    async def enviar_recuperacion(self, correo: str, enlace: str) -> None: ...


@dataclass(frozen=True)
class ProductoResumen:
    id: int
    codigo_ean: str
    nombre: str
    marca: str | None
    presentacion: str | None
    url_imagen: str | None


@dataclass(frozen=True)
class PrecioProducto:
    comercio_id: int
    comercio: str
    sucursal_id: int
    sucursal: str
    direccion: str | None
    localidad: str | None
    provincia: str | None
    precio: float
    fecha_vigencia: datetime
    distancia_km: float | None


@dataclass(frozen=True)
class SucursalGeo:
    id: int
    nombre: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    latitud: float
    longitud: float
    distancia_km: float | None
    comercio_id: int
    comercio_marca: str | None
    bandera_nombre: str | None
    bandera_logo_url: str | None


@dataclass(frozen=True)
class ItemCarrito:
    id: int
    carrito_id: int
    producto_id: int
    cantidad: int


@dataclass(frozen=True)
class Carrito:
    id: int
    usuario_id: int
    titulo: str | None
    activo: bool
    fecha_ultima_edicion: datetime
    cantidad_items: int


@dataclass(frozen=True)
class EliminacionCarrito:
    eliminado: bool
    era_activo: bool


class ICatalogoRepository(Protocol):
    def buscar_por_ean(self, codigo_ean: str) -> ProductoResumen | None: ...

    def buscar_por_nombre(self, texto: str, limite: int) -> list[ProductoResumen]: ...

    def obtener_producto(self, producto_id: int) -> ProductoResumen | None: ...

    def obtener_precios_producto(
        self,
        producto_id: int,
        *,
        lat: float | None,
        lon: float | None,
        radio_km: int | None,
        limite: int | None = None,
    ) -> list[PrecioProducto]: ...


class ISucursalesRepository(Protocol):
    def sucursales_cercanas(self, lat: float, lon: float, radio_km: int) -> list[SucursalGeo]: ...


class ICarritoRepository(Protocol):
    def listar_carritos(self, usuario_id: int) -> list[Carrito]: ...

    def crear_carrito_activo(self, usuario_id: int, titulo: str | None = None) -> Carrito: ...

    def obtener_carrito(self, usuario_id: int, carrito_id: int) -> Carrito | None: ...

    def actualizar_titulo(
        self,
        usuario_id: int,
        carrito_id: int,
        titulo: str | None,
    ) -> Carrito | None: ...

    def activar_carrito(self, usuario_id: int, carrito_id: int) -> Carrito | None: ...

    def eliminar_carrito(self, usuario_id: int, carrito_id: int) -> EliminacionCarrito: ...

    def promover_activo_o_crear(self, usuario_id: int) -> Carrito: ...

    def obtener_item_por_producto(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
    ) -> ItemCarrito | None: ...

    def agregar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        producto_id: int,
        cantidad: int,
    ) -> ItemCarrito: ...

    def actualizar_item(
        self,
        usuario_id: int,
        carrito_id: int,
        item_id: int,
        cantidad: int,
    ) -> ItemCarrito | None: ...

    def eliminar_item(self, usuario_id: int, carrito_id: int, item_id: int) -> bool: ...

    def listar_items_con_producto(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> list[tuple[ItemCarrito, ProductoResumen | None]]: ...
