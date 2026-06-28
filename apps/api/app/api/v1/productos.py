from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.domain.catalogo import (
    CatalogoNotFoundError,
    CatalogoService,
    CatalogoValidationError,
    PrecioProductoResultado,
)
from app.domain.ports import ProductoResumen
from app.infra.catalogo_repo import CatalogoRepository

router = APIRouter(prefix="/productos", tags=["productos"])


class ProductoResumenResponse(BaseModel):
    id: int
    codigo_ean: str
    nombre: str
    marca: str | None
    presentacion: str | None
    url_imagen: str | None


class BuscarProductosResponse(BaseModel):
    items: list[ProductoResumenResponse]
    total: int


class PrecioProductoResponse(BaseModel):
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


class DetalleProductoResponse(BaseModel):
    producto: ProductoResumenResponse
    precios: list[PrecioProductoResponse]
    filtro_radio_activo: bool
    mensaje: str | None


def get_catalogo_service() -> CatalogoService:
    return CatalogoService(catalogo_repo=CatalogoRepository())


def _to_producto_response(producto: ProductoResumen) -> ProductoResumenResponse:
    return ProductoResumenResponse(
        id=producto.id,
        codigo_ean=producto.codigo_ean,
        nombre=producto.nombre,
        marca=producto.marca,
        presentacion=producto.presentacion,
        url_imagen=producto.url_imagen,
    )


def _to_precio_response(precio: PrecioProductoResultado) -> PrecioProductoResponse:
    return PrecioProductoResponse(
        comercio_id=precio.comercio_id,
        comercio=precio.comercio,
        sucursal_id=precio.sucursal_id,
        sucursal=precio.sucursal,
        direccion=precio.direccion,
        localidad=precio.localidad,
        provincia=precio.provincia,
        precio=precio.precio,
        fecha_vigencia=precio.fecha_vigencia,
        distancia_km=precio.distancia_km,
        precio_minimo=precio.precio_minimo,
    )


@router.get("/buscar", response_model=BuscarProductosResponse)
def buscar_productos(
    q: str,
    limit: int = Query(default=5, ge=1, le=5),
    service: CatalogoService = Depends(get_catalogo_service),
) -> BuscarProductosResponse:
    try:
        items = service.buscar(q=q, limite=limit)
    except CatalogoValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "codigo": "PARAM_INVALIDO",
                    "mensaje": str(error),
                    "campos": ["q"],
                }
            },
        ) from error

    response_items = [_to_producto_response(item) for item in items]
    return BuscarProductosResponse(items=response_items, total=len(response_items))


@router.get("/{producto_id}", response_model=DetalleProductoResponse)
def detalle_producto(
    producto_id: int,
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
    radio_km: int | None = Query(default=None, ge=1),
    service: CatalogoService = Depends(get_catalogo_service),
) -> DetalleProductoResponse:
    if any(param is not None for param in (lat, lon, radio_km)) and not all(
        param is not None for param in (lat, lon, radio_km)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "codigo": "PARAM_INVALIDO",
                    "mensaje": "lat, lon y radio_km deben enviarse juntos.",
                    "campos": ["lat", "lon", "radio_km"],
                }
            },
        )

    try:
        result = service.detalle(producto_id=producto_id, lat=lat, lon=lon, radio_km=radio_km)
    except CatalogoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "codigo": "NO_ENCONTRADO",
                    "mensaje": str(error),
                }
            },
        ) from error

    return DetalleProductoResponse(
        producto=_to_producto_response(result.producto),
        precios=[_to_precio_response(precio) for precio in result.precios],
        filtro_radio_activo=result.filtro_radio_activo,
        mensaje=result.mensaje,
    )
