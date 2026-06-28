from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.domain.ports import SucursalGeo
from app.domain.sucursales_service import SucursalesService, SucursalesValidationError
from app.infra.sucursales_repo import SucursalesRepository

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])


class SucursalGeoResponse(BaseModel):
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

    model_config = {"from_attributes": True}


def get_sucursales_service() -> SucursalesService:
    return SucursalesService(sucursales_repo=SucursalesRepository())


def _to_sucursal_response(sucursal: SucursalGeo) -> SucursalGeoResponse:
    return SucursalGeoResponse.model_validate(sucursal)


@router.get("", response_model=list[SucursalGeoResponse])
def listar_sucursales(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    radio_km: int = Query(default=10, ge=1, le=50),
    service: SucursalesService = Depends(get_sucursales_service),
) -> list[SucursalGeoResponse]:
    try:
        sucursales = service.get_sucursales_cercanas(lat=lat, lon=lon, radio_km=radio_km)
    except SucursalesValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "codigo": "PARAM_INVALIDO",
                    "mensaje": str(error),
                    "campos": ["lat", "lon", "radio_km"],
                }
            },
        ) from error

    return [_to_sucursal_response(sucursal) for sucursal in sucursales]
