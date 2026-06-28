import re
from dataclasses import dataclass

from app.domain.ports import ICatalogoRepository, PrecioProducto, ProductoResumen

_EAN_RE = re.compile(r"^\d{13}$")
_SOLO_DIGITOS_RE = re.compile(r"^\d+$")
LIMITE_PRECIOS_CERCANOS = 6


class CatalogoError(Exception):
    pass


class CatalogoValidationError(CatalogoError):
    pass


class CatalogoNotFoundError(CatalogoError):
    pass


@dataclass(frozen=True)
class PrecioProductoResultado:
    comercio_id: int
    comercio: str
    sucursal_id: int
    sucursal: str
    direccion: str | None
    localidad: str | None
    provincia: str | None
    precio: float
    fecha_vigencia: str
    distancia_km: float | None
    precio_minimo: bool


@dataclass(frozen=True)
class DetalleProductoResultado:
    producto: ProductoResumen
    precios: list[PrecioProductoResultado]
    filtro_radio_activo: bool
    mensaje: str | None


class CatalogoService:
    def __init__(self, catalogo_repo: ICatalogoRepository) -> None:
        self._catalogo_repo = catalogo_repo

    def buscar(self, q: str, limite: int = 5) -> list[ProductoResumen]:
        termino = q.strip()
        if not termino:
            raise CatalogoValidationError("El parámetro q es obligatorio")

        limite_normalizado = max(1, min(limite, 5))

        if _EAN_RE.match(termino):
            producto = self._catalogo_repo.buscar_por_ean(termino)
            return [producto] if producto is not None else []

        if _SOLO_DIGITOS_RE.match(termino):
            raise CatalogoValidationError("El EAN debe tener exactamente 13 dígitos")

        if len(termino) < 4:
            raise CatalogoValidationError("La búsqueda por nombre requiere al menos 4 caracteres")

        return self._catalogo_repo.buscar_por_nombre(termino, limite_normalizado)

    def detalle(
        self,
        producto_id: int,
        *,
        lat: float | None = None,
        lon: float | None = None,
        radio_km: int | None = None,
    ) -> DetalleProductoResultado:
        producto = self._catalogo_repo.obtener_producto(producto_id)
        if producto is None:
            raise CatalogoNotFoundError("Producto no encontrado")

        filtro_radio_activo = lat is not None and lon is not None and radio_km is not None
        precios = self._catalogo_repo.obtener_precios_producto(
            producto_id,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            limite=LIMITE_PRECIOS_CERCANOS if filtro_radio_activo else None,
        )

        precio_minimo = min((precio.precio for precio in precios), default=None)
        precios_resultado = [self._to_result(precio, precio_minimo) for precio in precios]

        mensaje: str | None = None
        if not filtro_radio_activo:
            mensaje = "Indicá tu ubicación para ver precios cercanos"
        elif not precios_resultado:
            mensaje = "No hay comercios dentro del radio indicado"

        return DetalleProductoResultado(
            producto=producto,
            precios=precios_resultado,
            filtro_radio_activo=filtro_radio_activo,
            mensaje=mensaje,
        )

    @staticmethod
    def _to_result(precio: PrecioProducto, precio_minimo: float | None) -> PrecioProductoResultado:
        return PrecioProductoResultado(
            comercio_id=precio.comercio_id,
            comercio=precio.comercio,
            sucursal_id=precio.sucursal_id,
            sucursal=precio.sucursal,
            direccion=precio.direccion,
            localidad=precio.localidad,
            provincia=precio.provincia,
            precio=precio.precio,
            fecha_vigencia=precio.fecha_vigencia.date().isoformat(),
            distancia_km=precio.distancia_km,
            precio_minimo=precio_minimo is not None and precio.precio == precio_minimo,
        )
