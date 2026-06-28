from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

PreferenciaOptimizacion = Literal[
    "MENOR_PRECIO",
    "MENOR_DESPLAZAMIENTO",
    "BALANCEADO",
]


@dataclass(frozen=True)
class ConfiguracionOptimizacion:
    radio_km: int
    max_paradas: int
    preferencia: PreferenciaOptimizacion
    origen_lat: float
    origen_lon: float
    por_defecto_aplicado: tuple[str, ...]
    origen_direccion: str | None = None
    origen_modalidad: str | None = None


@dataclass(frozen=True)
class ItemCarritoOptimizacion:
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    url_imagen: str | None = None


@dataclass(frozen=True)
class OfertaItemCandidata:
    item_carrito_id: int
    producto_id: int
    precio_id: int
    sucursal_id: int
    sucursal: str
    comercio: str
    direccion: str | None
    localidad: str | None
    provincia: str | None
    latitud: float
    longitud: float
    precio_unitario: float
    distancia_km: float | None = None
    bandera_nombre: str | None = None
    bandera_logo_url: str | None = None


@dataclass(frozen=True)
class EntradaOptimizacion:
    items: list[ItemCarritoOptimizacion]
    ofertas: list[OfertaItemCandidata]
    max_paradas: int
    preferencia: PreferenciaOptimizacion
    origen_lat: float
    origen_lon: float
    distancia_origen_sucursal_km: dict[int, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ItemAsignadoResultado:
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_id: int
    precio_unitario: float
    subtotal: float
    url_imagen: str | None = None


@dataclass(frozen=True)
class AsignacionSucursalResultado:
    sucursal_id: int
    sucursal: str
    comercio: str
    direccion: str | None
    localidad: str | None
    provincia: str | None
    latitud: float
    longitud: float
    subtotal: float
    items: list[ItemAsignadoResultado]
    distancia_km: float | None = None
    bandera_nombre: str | None = None
    bandera_logo_url: str | None = None


@dataclass(frozen=True)
class ItemNoAsignadoResultado:
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    url_imagen: str | None = None


@dataclass(frozen=True)
class ParadaResultado:
    orden: int
    sucursal_id: int | None
    nombre: str
    es_origen: bool
    es_adicional: bool
    distancia_desde_anterior_km: float
    productos: list[str]


@dataclass(frozen=True)
class RuteoResultado:
    distancia_total_km: float
    paradas: list[ParadaResultado]


@dataclass(frozen=True)
class ResultadoDistribucion:
    fecha_calculo: datetime
    costo_total_estimado: float
    ahorro_estimado: float | None
    configuracion: ConfiguracionOptimizacion
    asignaciones: list[AsignacionSucursalResultado]
    items_no_asignados: list[ItemNoAsignadoResultado]
    ruteo: RuteoResultado
    mensaje: str | None = None
    id: int | None = None


class DistribucionError(Exception):
    pass


class DistribucionCarritoVacioError(DistribucionError):
    pass


class DistribucionConfigError(DistribucionError):
    pass


class DistribucionNoEncontradaError(DistribucionError):
    pass


class IMotorOptimizacion(Protocol):
    def distribuir(
        self, entrada: EntradaOptimizacion
    ) -> tuple[
        list[AsignacionSucursalResultado],
        list[ItemNoAsignadoResultado],
    ]: ...


class IPreferenciasRepository(Protocol):
    def obtener_configuracion(self, usuario_id: int) -> ConfiguracionOptimizacion: ...

    def guardar_configuracion(
        self,
        usuario_id: int,
        *,
        radio_km: int | None,
        max_paradas: int | None,
        preferencia: PreferenciaOptimizacion | None,
        origen_lat: float | None,
        origen_lon: float | None,
        origen_direccion: str | None,
        origen_modalidad: str | None,
    ) -> ConfiguracionOptimizacion: ...


class IDistribucionRepository(Protocol):
    def obtener_items_carrito(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> list[ItemCarritoOptimizacion]: ...

    def obtener_ofertas_candidatas(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        origen_lat: float,
        origen_lon: float,
        radio_km: int,
    ) -> list[OfertaItemCandidata]: ...

    def calcular_costo_referencia(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        origen_lat: float,
        origen_lon: float,
        radio_km: int,
    ) -> float | None: ...

    def guardar_distribucion(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        configuracion: ConfiguracionOptimizacion,
        asignaciones: list[AsignacionSucursalResultado],
        items_no_asignados: list[ItemNoAsignadoResultado],
        ruteo: RuteoResultado,
        costo_total_estimado: float,
        ahorro_estimado: float | None,
    ) -> ResultadoDistribucion: ...

    def obtener_distribucion_vigente(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> ResultadoDistribucion | None: ...
