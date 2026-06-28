from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.security import (
    crear_token_acceso,
    generar_token_recuperacion,
    hashear_password,
    hashear_token_recuperacion,
    verificar_password,
)
from app.domain.ports import IAuthRepository, IEmailSender, ItemCarritoAnonimo, ITokenRepository


class AuthError(Exception):
    pass


class AuthConflictError(AuthError):
    pass


class AuthUnauthorizedError(AuthError):
    pass


class AuthBadRequestError(AuthError):
    pass


@dataclass(frozen=True)
class UsuarioPublico:
    id: int
    nombre: str
    correo: str


@dataclass(frozen=True)
class AuthResult:
    usuario: UsuarioPublico
    token: str


class AuthService:
    def __init__(
        self,
        auth_repo: IAuthRepository,
        token_repo: ITokenRepository,
        email_sender: IEmailSender,
    ) -> None:
        self._auth_repo = auth_repo
        self._token_repo = token_repo
        self._email_sender = email_sender

    def registrar(
        self,
        *,
        nombre: str,
        correo: str,
        password: str,
        carrito_anonimo: list[ItemCarritoAnonimo],
    ) -> AuthResult:
        if len(password) < 8:
            raise AuthBadRequestError("La contraseña debe tener al menos 8 caracteres")

        existente = self._auth_repo.obtener_por_correo(correo)
        if existente is not None:
            raise AuthConflictError("El correo ya está registrado")

        password_hash = hashear_password(password)
        usuario_id = self._auth_repo.crear_usuario(nombre, correo, password_hash)
        if carrito_anonimo:
            self._auth_repo.convertir_carrito_anonimo(usuario_id, carrito_anonimo)
        else:
            self._auth_repo.activar_ultimo_carrito(usuario_id)

        usuario = self._auth_repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise AuthBadRequestError("No se pudo recuperar el usuario creado")

        return AuthResult(
            usuario=UsuarioPublico(id=usuario.id, nombre=usuario.nombre, correo=usuario.correo),
            token=crear_token_acceso(usuario.id, usuario.correo),
        )

    def login(
        self,
        *,
        correo: str,
        password: str,
        carrito_anonimo: list[ItemCarritoAnonimo],
    ) -> AuthResult:
        usuario = self._auth_repo.obtener_por_correo(correo)
        if usuario is None or not verificar_password(password, usuario.password_hash):
            raise AuthUnauthorizedError("Credenciales inválidas")

        if carrito_anonimo:
            self._auth_repo.convertir_carrito_anonimo(usuario.id, carrito_anonimo)
        else:
            self._auth_repo.activar_ultimo_carrito(usuario.id)

        return AuthResult(
            usuario=UsuarioPublico(id=usuario.id, nombre=usuario.nombre, correo=usuario.correo),
            token=crear_token_acceso(usuario.id, usuario.correo),
        )

    async def recuperar(self, *, correo: str) -> None:
        usuario = self._auth_repo.obtener_por_correo(correo)
        if usuario is None:
            return

        token = generar_token_recuperacion()
        token_hash = hashear_token_recuperacion(token)
        settings = get_settings()
        expira_en = datetime.now(UTC) + timedelta(seconds=settings.reset_token_ttl_seconds)
        self._token_repo.guardar_hash(usuario.id, token_hash, expira_en)
        enlace = f"{settings.auth_url}/restablecer?token={token}"
        await self._email_sender.enviar_recuperacion(correo, enlace)

    def restablecer(self, *, token: str, nueva_password: str) -> AuthResult:
        if len(nueva_password) < 8:
            raise AuthBadRequestError("La contraseña debe tener al menos 8 caracteres")

        token_hash = hashear_token_recuperacion(token)
        token_info = self._token_repo.validar(token_hash)
        if token_info is None:
            raise AuthBadRequestError("El enlace de recuperación es inválido o expiró")

        password_hash = hashear_password(nueva_password)
        self._auth_repo.actualizar_password(token_info.usuario_id, password_hash)
        self._token_repo.marcar_usado(token_hash)

        usuario = self._auth_repo.obtener_por_id(token_info.usuario_id)
        if usuario is None:
            raise AuthBadRequestError("No se pudo recuperar el usuario")

        return AuthResult(
            usuario=UsuarioPublico(id=usuario.id, nombre=usuario.nombre, correo=usuario.correo),
            token=crear_token_acceso(usuario.id, usuario.correo),
        )

    def actualizar_perfil(self, *, usuario_id: int, nombre: str) -> UsuarioPublico:
        if not nombre.strip() or len(nombre.strip()) < 2:
            raise AuthBadRequestError("El nombre debe tener al menos 2 caracteres")

        self._auth_repo.actualizar_nombre(usuario_id, nombre.strip())

        usuario = self._auth_repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise AuthBadRequestError("Usuario no encontrado")

        return UsuarioPublico(id=usuario.id, nombre=usuario.nombre, correo=usuario.correo)
