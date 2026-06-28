from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_current_user
from app.api.v1.preferencias import get_distribucion_service
from app.api.v1.productos import ProductoResumenResponse, _to_producto_response
from app.domain.carrito import (
    CarritoForbiddenError,
    CarritoNotFoundError,
    CarritoService,
    CarritoValidationError,
)
from app.domain.optimizacion import (
    DistribucionCarritoVacioError,
    DistribucionConfigError,
    DistribucionNoEncontradaError,
    ResultadoDistribucion,
)
from app.domain.ports import Carrito, ItemCarrito, ProductoResumen
from app.domain.servicios.distribucion import DistribucionService
from app.infra.carrito_repo import CarritoRepository

router = APIRouter(prefix="/carritos", tags=["carritos"])


class CarritoResponse(BaseModel):
    id: int
    titulo: str | None
    activo: bool
    cantidad_items: int
    fecha_ultima_edicion: datetime


class ListarCarritosResponse(BaseModel):
    items: list[CarritoResponse]
    total: int


class ItemCarritoResponse(BaseModel):
    id: int
    carrito_id: int
    producto_id: int
    cantidad: int
    producto: ProductoResumenResponse | None = None


class DetalleCarritoResponse(BaseModel):
    carrito: CarritoResponse
    items: list[ItemCarritoResponse]


class CarritoDetalleResponse(BaseModel):
    id: int
    titulo: str | None
    activo: bool
    items: list[ItemCarritoResponse]


class CrearCarritoResponse(BaseModel):
    id: int
    titulo: str | None
    activo: bool
    items: list[ItemCarritoResponse]


class ActualizarCarritoRequest(BaseModel):
    titulo: str | None = None
    activo: bool | None = None


class AgregarItemRequest(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(ge=1, le=99)


class ActualizarItemRequest(BaseModel):
    cantidad: int = Field(ge=1, le=99)


class UbicacionReferenciaRequest(BaseModel):
    latitud: float
    longitud: float
    direccion: str | None = None
    modalidad: str | None = None


class DistribuirCarritoRequest(BaseModel):
    radio_km: int | None = Field(default=None, ge=1, le=50)
    max_paradas: int | None = Field(default=None, ge=1, le=5)
    preferencia: str | None = None
    ubicacion_referencia: UbicacionReferenciaRequest | None = None


class ConfiguracionDistribucionResponse(BaseModel):
    radio_km: int
    max_paradas: int
    preferencia: str
    por_defecto_aplicado: list[str]


class ItemAsignadoDistribucionResponse(BaseModel):
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    url_imagen: str | None = None


class AsignacionSucursalDistribucionResponse(BaseModel):
    sucursal_id: int
    sucursal: str
    comercio: str
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    latitud: float
    longitud: float
    distancia_km: float | None = None
    bandera_nombre: str | None = None
    bandera_logo_url: str | None = None
    subtotal: float
    items: list[ItemAsignadoDistribucionResponse]


class ItemNoAsignadoResponse(BaseModel):
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    url_imagen: str | None = None


class ParadaRuteoResponse(BaseModel):
    orden: int
    sucursal_id: int | None
    nombre: str
    distancia_desde_anterior_km: float
    es_origen: bool
    es_adicional: bool
    productos: list[str]


class RuteoResponse(BaseModel):
    distancia_total_km: float
    paradas: list[ParadaRuteoResponse]


class CarritoDistribuidoResponse(BaseModel):
    id: int | None = None
    fecha_calculo: datetime
    costo_total_estimado: float
    ahorro_estimado: float | None
    configuracion: ConfiguracionDistribucionResponse
    asignaciones: list[AsignacionSucursalDistribucionResponse]
    items_no_asignados: list[ItemNoAsignadoResponse]
    ruteo: RuteoResponse
    mensaje: str | None = None


def get_carrito_service() -> CarritoService:
    return CarritoService(carrito_repo=CarritoRepository())


def _to_carrito_response(carrito: Carrito) -> CarritoResponse:
    return CarritoResponse(
        id=carrito.id,
        titulo=carrito.titulo,
        activo=carrito.activo,
        cantidad_items=carrito.cantidad_items,
        fecha_ultima_edicion=carrito.fecha_ultima_edicion,
    )


def _to_item_response(
    item: ItemCarrito, producto: ProductoResumenResponse | None = None
) -> ItemCarritoResponse:
    return ItemCarritoResponse(
        id=item.id,
        carrito_id=item.carrito_id,
        producto_id=item.producto_id,
        cantidad=item.cantidad,
        producto=producto,
    )


def _to_carrito_detalle_response(
    carrito: Carrito,
    items: list[tuple[ItemCarrito, ProductoResumen | None]],
) -> CarritoDetalleResponse:
    return CarritoDetalleResponse(
        id=carrito.id,
        titulo=carrito.titulo,
        activo=carrito.activo,
        items=[
            _to_item_response(
                item,
                _to_producto_response(producto) if producto is not None else None,
            )
            for item, producto in items
        ],
    )


def _to_distribucion_response(resultado: ResultadoDistribucion) -> CarritoDistribuidoResponse:
    return CarritoDistribuidoResponse(
        id=resultado.id,
        fecha_calculo=resultado.fecha_calculo,
        costo_total_estimado=resultado.costo_total_estimado,
        ahorro_estimado=resultado.ahorro_estimado,
        configuracion=ConfiguracionDistribucionResponse(
            radio_km=resultado.configuracion.radio_km,
            max_paradas=resultado.configuracion.max_paradas,
            preferencia=resultado.configuracion.preferencia,
            por_defecto_aplicado=list(resultado.configuracion.por_defecto_aplicado),
        ),
        asignaciones=[
            AsignacionSucursalDistribucionResponse(
                sucursal_id=a.sucursal_id,
                sucursal=a.sucursal,
                comercio=a.comercio,
                direccion=a.direccion,
                localidad=a.localidad,
                provincia=a.provincia,
                latitud=a.latitud,
                longitud=a.longitud,
                distancia_km=a.distancia_km,
                bandera_nombre=a.bandera_nombre,
                bandera_logo_url=a.bandera_logo_url,
                subtotal=a.subtotal,
                items=[
                    ItemAsignadoDistribucionResponse(
                        item_carrito_id=i.item_carrito_id,
                        producto_id=i.producto_id,
                        nombre_producto=i.nombre_producto,
                        cantidad=i.cantidad,
                        precio_unitario=i.precio_unitario,
                        subtotal=i.subtotal,
                        url_imagen=i.url_imagen,
                    )
                    for i in a.items
                ],
            )
            for a in resultado.asignaciones
        ],
        items_no_asignados=[
            ItemNoAsignadoResponse(
                item_carrito_id=i.item_carrito_id,
                producto_id=i.producto_id,
                nombre_producto=i.nombre_producto,
                cantidad=i.cantidad,
                url_imagen=i.url_imagen,
            )
            for i in resultado.items_no_asignados
        ],
        ruteo=RuteoResponse(
            distancia_total_km=resultado.ruteo.distancia_total_km,
            paradas=[
                ParadaRuteoResponse(
                    orden=p.orden,
                    sucursal_id=p.sucursal_id,
                    nombre=p.nombre,
                    distancia_desde_anterior_km=p.distancia_desde_anterior_km,
                    es_origen=p.es_origen,
                    es_adicional=p.es_adicional,
                    productos=p.productos,
                )
                for p in resultado.ruteo.paradas
            ],
        ),
        mensaje=resultado.mensaje,
    )


@router.get("", response_model=ListarCarritosResponse)
def listar_carritos(
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> ListarCarritosResponse:
    usuario_id = int(current_user["id"])
    carritos = service.listar(usuario_id)
    items = [_to_carrito_response(carrito) for carrito in carritos]
    return ListarCarritosResponse(items=items, total=len(items))


@router.post("", response_model=CrearCarritoResponse, status_code=status.HTTP_201_CREATED)
def crear_carrito(
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> CrearCarritoResponse:
    carrito = service.crear(usuario_id=int(current_user["id"]))
    return CrearCarritoResponse(
        id=carrito.id,
        titulo=carrito.titulo,
        activo=carrito.activo,
        items=[],
    )


@router.get("/activo", response_model=CarritoDetalleResponse)
def obtener_carrito_activo(
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> CarritoDetalleResponse:
    usuario_id = int(current_user["id"])
    try:
        carrito_activo, items = service.obtener_activo_detalle(usuario_id)
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error
    return _to_carrito_detalle_response(carrito_activo, items)


@router.get("/{carrito_id}", response_model=DetalleCarritoResponse)
def obtener_carrito(
    carrito_id: int,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> DetalleCarritoResponse:
    try:
        carrito = service.obtener(usuario_id=int(current_user["id"]), carrito_id=carrito_id)
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error

    return DetalleCarritoResponse(carrito=_to_carrito_response(carrito), items=[])


@router.patch("/{carrito_id}", response_model=CarritoResponse)
def actualizar_carrito(
    carrito_id: int,
    payload: ActualizarCarritoRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> CarritoResponse:
    if payload.titulo is None and payload.activo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "codigo": "PARAM_INVALIDO",
                    "mensaje": "Debés enviar al menos un campo para actualizar.",
                    "campos": ["titulo", "activo"],
                }
            },
        )

    usuario_id = int(current_user["id"])
    try:
        if payload.activo is True:
            carrito = service.activar(usuario_id=usuario_id, carrito_id=carrito_id)
        elif payload.titulo is not None:
            carrito = service.renombrar(
                usuario_id=usuario_id,
                carrito_id=carrito_id,
                titulo=payload.titulo,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "codigo": "PARAM_INVALIDO",
                        "mensaje": "El campo activo solo acepta true para activar un carrito.",
                        "campos": ["activo"],
                    }
                },
            )
    except CarritoForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"codigo": "SIN_PERMISOS", "mensaje": str(error)}},
        ) from error
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error

    return _to_carrito_response(carrito)


@router.delete("/{carrito_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_carrito(
    carrito_id: int,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> Response:
    try:
        service.eliminar(usuario_id=int(current_user["id"]), carrito_id=carrito_id)
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{carrito_id}/items",
    response_model=ItemCarritoResponse,
    status_code=status.HTTP_201_CREATED,
)
def agregar_item(
    carrito_id: int,
    response: Response,
    payload: AgregarItemRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> ItemCarritoResponse:
    try:
        resultado = service.agregar_item_detallado(
            usuario_id=int(current_user["id"]),
            carrito_id=carrito_id,
            producto_id=payload.producto_id,
            cantidad=payload.cantidad,
        )
    except CarritoValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "codigo": "PARAM_INVALIDO",
                    "mensaje": str(error),
                    "campos": ["cantidad"],
                }
            },
        ) from error
    except CarritoForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"codigo": "SIN_PERMISOS", "mensaje": str(error)}},
        ) from error
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error

    if not resultado.creado:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    return _to_item_response(resultado.item)


@router.patch("/{carrito_id}/items/{item_id}", response_model=ItemCarritoResponse)
def actualizar_item(
    carrito_id: int,
    item_id: int,
    payload: ActualizarItemRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> ItemCarritoResponse:
    try:
        item = service.editar_item(
            usuario_id=int(current_user["id"]),
            carrito_id=carrito_id,
            item_id=item_id,
            cantidad=payload.cantidad,
        )
    except CarritoValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "codigo": "PARAM_INVALIDO",
                    "mensaje": str(error),
                    "campos": ["cantidad"],
                }
            },
        ) from error
    except CarritoForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"codigo": "SIN_PERMISOS", "mensaje": str(error)}},
        ) from error
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error

    return _to_item_response(item)


@router.delete("/{carrito_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_item(
    carrito_id: int,
    item_id: int,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CarritoService = Depends(get_carrito_service),
) -> Response:
    try:
        service.eliminar_item(
            usuario_id=int(current_user["id"]),
            carrito_id=carrito_id,
            item_id=item_id,
        )
    except CarritoForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"codigo": "SIN_PERMISOS", "mensaje": str(error)}},
        ) from error
    except CarritoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{carrito_id}/distribuir",
    response_model=CarritoDistribuidoResponse,
    summary="Calcular distribución optimizada del carrito",
    description=(
        "Ejecuta la optimización con la configuración efectiva del usuario. "
        "Si se provee body, esos parámetros se usan para esta distribución "
        "sin guardar en perfil. "
        "Si no se provee body, se usan las preferencias guardadas del usuario. "
        "Si faltan `max_paradas` o `preferencia` en preferencias, se aplican defaults "
        "(`max_paradas=3`, `preferencia=MENOR_PRECIO`) y se informan en "
        "`configuracion.por_defecto_aplicado`. "
        "Ante timeout interno del solver, el backend aplica fallback factible para "
        "responder dentro del SLA."
    ),
)
def distribuir_carrito(
    carrito_id: int,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: DistribucionService = Depends(get_distribucion_service),
    body: DistribuirCarritoRequest | None = None,
) -> CarritoDistribuidoResponse:
    try:
        kwargs: dict = {}
        if body is not None:
            if body.radio_km is not None:
                kwargs["radio_km"] = body.radio_km
            if body.max_paradas is not None:
                kwargs["max_paradas"] = body.max_paradas
            if body.preferencia is not None:
                kwargs["preferencia"] = body.preferencia
            if body.ubicacion_referencia is not None:
                kwargs["origen_lat"] = body.ubicacion_referencia.latitud
                kwargs["origen_lon"] = body.ubicacion_referencia.longitud
                kwargs["origen_direccion"] = body.ubicacion_referencia.direccion
                kwargs["origen_modalidad"] = body.ubicacion_referencia.modalidad

        resultado = service.distribuir(int(current_user["id"]), carrito_id, **kwargs)
    except DistribucionCarritoVacioError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"codigo": "CARRITO_VACIO", "mensaje": str(error)}},
        ) from error
    except DistribucionConfigError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"codigo": "CONFIG_INVALIDA", "mensaje": str(error)}},
        ) from error

    return _to_distribucion_response(resultado)


@router.get(
    "/{carrito_id}/distribucion",
    response_model=CarritoDistribuidoResponse,
    summary="Obtener distribución vigente del carrito",
    description=(
        "Devuelve la última distribución marcada como vigente para el carrito, "
        "incluyendo snapshot inmutable de configuración (`cfg_*`), asignaciones y ruteo."
    ),
)
def obtener_distribucion_vigente(
    carrito_id: int,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: DistribucionService = Depends(get_distribucion_service),
) -> CarritoDistribuidoResponse:
    try:
        resultado = service.obtener_distribucion_vigente(int(current_user["id"]), carrito_id)
    except DistribucionNoEncontradaError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error
    return _to_distribucion_response(resultado)
