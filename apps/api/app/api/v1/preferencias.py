from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_current_user
from app.domain.optimizacion import ConfiguracionOptimizacion, DistribucionConfigError
from app.domain.servicios.distribucion import DistribucionService
from app.infra.distribucion_repo import DistribucionRepository, PreferenciasRepository
from app.infra.geo_clients import OsrmClient
from app.infra.motor_ortools import MotorOrTools

router = APIRouter(prefix="/preferencias", tags=["preferencias"])


class UbicacionReferenciaPayload(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    direccion: str | None = None
    modalidad: str | None = None


class PreferenciasUpdateRequest(BaseModel):
    radio_km: int | None = Field(default=None, ge=1, le=50)
    max_paradas: int | None = Field(default=None, ge=1, le=5)
    modo_preferencia: Literal["MENOR_PRECIO", "MENOR_DESPLAZAMIENTO", "BALANCEADO"] | None = None
    ubicacion_referencia: UbicacionReferenciaPayload | None = None


class OrigenResponse(BaseModel):
    latitud: float
    longitud: float
    direccion: str | None = None
    modalidad: str | None = None


class ConfiguracionResponse(BaseModel):
    radio_km: int
    max_paradas: int
    preferencia: str
    origen: OrigenResponse
    por_defecto_aplicado: list[str]


def get_distribucion_service() -> DistribucionService:
    from app.core.config import get_settings

    settings = get_settings()
    return DistribucionService(
        preferencias_repo=PreferenciasRepository(),
        distribucion_repo=DistribucionRepository(),
        motor=MotorOrTools(),
        osrm_client=OsrmClient(settings.osrm_url),
    )


def _to_config_response(configuracion: ConfiguracionOptimizacion) -> ConfiguracionResponse:
    return ConfiguracionResponse(
        radio_km=configuracion.radio_km,
        max_paradas=configuracion.max_paradas,
        preferencia=configuracion.preferencia,
        origen=OrigenResponse(
            latitud=configuracion.origen_lat,
            longitud=configuracion.origen_lon,
            direccion=configuracion.origen_direccion,
            modalidad=configuracion.origen_modalidad,
        ),
        por_defecto_aplicado=list(configuracion.por_defecto_aplicado),
    )


@router.get("", response_model=ConfiguracionResponse)
def obtener_preferencias(
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: DistribucionService = Depends(get_distribucion_service),
) -> ConfiguracionResponse:
    try:
        config = service.obtener_preferencias(int(current_user["id"]))
    except DistribucionConfigError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"codigo": "CONFIG_INCOMPLETA", "mensaje": str(error)}},
        ) from error
    return _to_config_response(config)


@router.put("", response_model=ConfiguracionResponse)
def actualizar_preferencias(
    payload: PreferenciasUpdateRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: DistribucionService = Depends(get_distribucion_service),
) -> ConfiguracionResponse:
    ubicacion = payload.ubicacion_referencia
    try:
        config = service.guardar_preferencias(
            int(current_user["id"]),
            radio_km=payload.radio_km,
            max_paradas=payload.max_paradas,
            preferencia=payload.modo_preferencia,
            origen_lat=ubicacion.latitud if ubicacion is not None else None,
            origen_lon=ubicacion.longitud if ubicacion is not None else None,
            origen_direccion=ubicacion.direccion if ubicacion is not None else None,
            origen_modalidad=ubicacion.modalidad if ubicacion is not None else None,
        )
    except DistribucionConfigError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"codigo": "PARAM_INVALIDO", "mensaje": str(error)}},
        ) from error
    return _to_config_response(config)
