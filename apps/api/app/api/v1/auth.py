from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.api.v1.dependencies import get_current_user
from app.domain.auth import (
    AuthBadRequestError,
    AuthConflictError,
    AuthService,
    AuthUnauthorizedError,
)
from app.domain.ports import ItemCarritoAnonimo
from app.infra.auth_repo import AuthRepository
from app.infra.email import EmailSender

router = APIRouter(prefix="/auth", tags=["auth"])


class ItemCarritoAnonimoPayload(BaseModel):
    producto_id: int = Field(alias="productoId", gt=0)
    cantidad: int = Field(ge=1, le=99)

    def to_domain(self) -> ItemCarritoAnonimo:
        return ItemCarritoAnonimo(producto_id=self.producto_id, cantidad=self.cantidad)


class RegistroRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=255)
    carrito_anonimo: list[ItemCarritoAnonimoPayload] = Field(
        default_factory=list,
        alias="carritoAnonimo",
    )


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=255)
    carrito_anonimo: list[ItemCarritoAnonimoPayload] = Field(
        default_factory=list,
        alias="carritoAnonimo",
    )


class RecuperarRequest(BaseModel):
    correo: EmailStr


class RestablecerRequest(BaseModel):
    token: str = Field(min_length=10)
    nueva_password: str = Field(min_length=8, max_length=255, alias="nuevaPassword")


class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    correo: EmailStr


class AuthResponse(BaseModel):
    usuario: UsuarioResponse
    token: str


class MensajeResponse(BaseModel):
    mensaje: str


class ActualizarPerfilRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)


class PerfilResponse(BaseModel):
    id: int
    nombre: str
    correo: EmailStr


def get_auth_service() -> AuthService:
    repo = AuthRepository()
    return AuthService(auth_repo=repo, token_repo=repo, email_sender=EmailSender())


def _mapear_error(error: Exception) -> HTTPException:
    if isinstance(error, AuthConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"codigo": "CORREO_DUPLICADO", "mensaje": str(error)}},
        )
    if isinstance(error, AuthUnauthorizedError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"codigo": "CREDENCIALES_INVALIDAS", "mensaje": str(error)}},
        )
    if isinstance(error, AuthBadRequestError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"codigo": "SOLICITUD_INVALIDA", "mensaje": str(error)}},
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"error": {"codigo": "ERROR_INTERNO", "mensaje": "Error interno del servidor."}},
    )


@router.post("/registro", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def registrar(
    payload: RegistroRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        result = service.registrar(
            nombre=payload.nombre,
            correo=payload.correo,
            password=payload.password,
            carrito_anonimo=[item.to_domain() for item in payload.carrito_anonimo],
        )
    except Exception as error:
        raise _mapear_error(error) from error

    return AuthResponse(
        usuario=UsuarioResponse(
            id=result.usuario.id,
            nombre=result.usuario.nombre,
            correo=result.usuario.correo,
        ),
        token=result.token,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> AuthResponse:
    try:
        result = service.login(
            correo=payload.correo,
            password=payload.password,
            carrito_anonimo=[item.to_domain() for item in payload.carrito_anonimo],
        )
    except Exception as error:
        raise _mapear_error(error) from error

    return AuthResponse(
        usuario=UsuarioResponse(
            id=result.usuario.id,
            nombre=result.usuario.nombre,
            correo=result.usuario.correo,
        ),
        token=result.token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    _: dict[str, int | str] = Depends(get_current_user),
) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/recuperar", response_model=MensajeResponse)
async def recuperar(
    payload: RecuperarRequest,
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    await service.recuperar(correo=payload.correo)
    return MensajeResponse(
        mensaje="Si el correo existe, vas a recibir un enlace para restablecer tu contraseña."
    )


@router.post("/restablecer", response_model=AuthResponse)
def restablecer(
    payload: RestablecerRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        result = service.restablecer(token=payload.token, nueva_password=payload.nueva_password)
    except Exception as error:
        raise _mapear_error(error) from error

    return AuthResponse(
        usuario=UsuarioResponse(
            id=result.usuario.id,
            nombre=result.usuario.nombre,
            correo=result.usuario.correo,
        ),
        token=result.token,
    )


@router.patch("/perfil", response_model=PerfilResponse)
def actualizar_perfil(
    payload: ActualizarPerfilRequest,
    current_user: dict[str, int | str] = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> PerfilResponse:
    try:
        result = service.actualizar_perfil(
            usuario_id=int(current_user["id"]),
            nombre=payload.nombre,
        )
    except Exception as error:
        raise _mapear_error(error) from error

    return PerfilResponse(id=result.id, nombre=result.nombre, correo=result.correo)
