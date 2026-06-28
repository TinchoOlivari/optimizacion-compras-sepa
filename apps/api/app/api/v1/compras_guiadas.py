from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_current_user
from app.domain.compra_guiada import (
    CompraGuiadaDetalle,
    CompraGuiadaNotFoundError,
    CompraGuiadaPendienteError,
    CompraGuiadaValidationError,
)
from app.domain.servicios.compra_guiada import CompraGuiadaService
from app.infra.compra_guiada_repo import CompraGuiadaRepository

router = APIRouter(prefix="/compras-guiadas", tags=["compras-guiadas"])


class IniciarCompraGuiadaRequest(BaseModel):
    carrito_distribuido_id: int = Field(gt=0)


class ActualizarProgresoItemRequest(BaseModel):
    estado: Literal["PENDIENTE", "CONSEGUIDO", "NO_ENCONTRADO", "DESCARTADO"]


class FinalizarCompraGuiadaRequest(BaseModel):
    confirmar_interrupcion: bool = False


class ItemCompraGuiadaResponse(BaseModel):
    progreso_item_id: int
    item_asignado_id: int
    item_carrito_id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    url_imagen: str | None = None
    estado: str


class ParadaCompraGuiadaResponse(BaseModel):
    orden: int
    sucursal_id: int
    sucursal: str
    comercio: str
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    distancia_desde_anterior_km: float
    bandera_nombre: str | None = None
    bandera_logo_url: str | None = None
    subtotal: float
    items: list[ItemCompraGuiadaResponse]


class CompraGuiadaResponse(BaseModel):
    id: int
    carrito_distribuido_id: int
    fecha_inicio: datetime
    fecha_cierre: datetime | None
    estado_cierre: str | None
    paradas: list[ParadaCompraGuiadaResponse]


def get_compra_guiada_service() -> CompraGuiadaService:
    return CompraGuiadaService(compra_repo=CompraGuiadaRepository())


@router.post("", response_model=CompraGuiadaResponse, status_code=status.HTTP_201_CREATED)
def iniciar_compra_guiada(
    body: IniciarCompraGuiadaRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CompraGuiadaService = Depends(get_compra_guiada_service),
) -> CompraGuiadaResponse:
    try:
        compra = service.iniciar(int(current_user["id"]), body.carrito_distribuido_id)
    except CompraGuiadaNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error
    return _to_response(compra)


@router.get("/{compra_id}", response_model=CompraGuiadaResponse)
def obtener_compra_guiada(
    compra_id: int,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CompraGuiadaService = Depends(get_compra_guiada_service),
) -> CompraGuiadaResponse:
    try:
        compra = service.obtener(int(current_user["id"]), compra_id)
    except CompraGuiadaNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error
    return _to_response(compra)


@router.patch("/{compra_id}/items/{progreso_item_id}", response_model=CompraGuiadaResponse)
def actualizar_progreso_item(
    compra_id: int,
    progreso_item_id: int,
    body: ActualizarProgresoItemRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CompraGuiadaService = Depends(get_compra_guiada_service),
) -> CompraGuiadaResponse:
    try:
        compra = service.actualizar_item(
            int(current_user["id"]),
            compra_id,
            progreso_item_id,
            body.estado,
        )
    except CompraGuiadaNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error
    return _to_response(compra)


@router.post("/{compra_id}/finalizar", response_model=CompraGuiadaResponse)
def finalizar_compra_guiada(
    compra_id: int,
    body: FinalizarCompraGuiadaRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: CompraGuiadaService = Depends(get_compra_guiada_service),
) -> CompraGuiadaResponse:
    try:
        compra = service.finalizar(
            int(current_user["id"]),
            compra_id,
            confirmar_interrupcion=body.confirmar_interrupcion,
        )
    except CompraGuiadaNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(error)}},
        ) from error
    except CompraGuiadaPendienteError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"codigo": "COMPRA_CON_PENDIENTES", "mensaje": str(error)}},
        ) from error
    except CompraGuiadaValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"codigo": "COMPRA_INVALIDA", "mensaje": str(error)}},
        ) from error
    return _to_response(compra)


def _to_response(compra: CompraGuiadaDetalle) -> CompraGuiadaResponse:
    return CompraGuiadaResponse(
        id=compra.id,
        carrito_distribuido_id=compra.carrito_distribuido_id,
        fecha_inicio=compra.fecha_inicio,
        fecha_cierre=compra.fecha_cierre,
        estado_cierre=compra.estado_cierre,
        paradas=[
            ParadaCompraGuiadaResponse(
                orden=parada.orden,
                sucursal_id=parada.sucursal_id,
                sucursal=parada.sucursal,
                comercio=parada.comercio,
                direccion=parada.direccion,
                localidad=parada.localidad,
                provincia=parada.provincia,
                distancia_desde_anterior_km=parada.distancia_desde_anterior_km,
                bandera_nombre=parada.bandera_nombre,
                bandera_logo_url=parada.bandera_logo_url,
                subtotal=parada.subtotal,
                items=[
                    ItemCompraGuiadaResponse(
                        progreso_item_id=item.progreso_item_id,
                        item_asignado_id=item.item_asignado_id,
                        item_carrito_id=item.item_carrito_id,
                        producto_id=item.producto_id,
                        nombre_producto=item.nombre_producto,
                        cantidad=item.cantidad,
                        precio_unitario=item.precio_unitario,
                        subtotal=item.subtotal,
                        url_imagen=item.url_imagen,
                        estado=item.estado,
                    )
                    for item in parada.items
                ],
            )
            for parada in compra.paradas
        ],
    )
