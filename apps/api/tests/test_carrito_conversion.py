from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.security import hashear_password
from app.domain.auth import AuthService
from app.domain.ports import ItemCarritoAnonimo, TokenRecuperacion, UsuarioAuth


class FakeAuthRepo:
    def __init__(self) -> None:
        self.usuario = UsuarioAuth(
            id=1,
            nombre="Ana",
            correo="ana@test.com",
            password_hash=hashear_password("password123"),
        )
        self.llamo_convertir = False
        self.llamo_activar = False

    def crear_usuario(self, nombre: str, correo: str, password_hash: str) -> int:
        self.usuario = UsuarioAuth(id=2, nombre=nombre, correo=correo, password_hash=password_hash)
        return 2

    def obtener_por_correo(self, correo: str) -> UsuarioAuth | None:
        if correo == self.usuario.correo:
            return self.usuario
        return None

    def obtener_por_id(self, usuario_id: int) -> UsuarioAuth | None:
        if usuario_id == self.usuario.id:
            return self.usuario
        return None

    def actualizar_password(self, usuario_id: int, password_hash: str) -> None:
        self.usuario = UsuarioAuth(
            id=usuario_id,
            nombre=self.usuario.nombre,
            correo=self.usuario.correo,
            password_hash=password_hash,
        )

    def convertir_carrito_anonimo(self, usuario_id: int, items: list[ItemCarritoAnonimo]) -> None:
        self.llamo_convertir = usuario_id > 0 and len(items) > 0

    def activar_ultimo_carrito(self, usuario_id: int) -> None:
        self.llamo_activar = usuario_id > 0


@dataclass
class FakeEmailSender:
    async def enviar_recuperacion(self, correo: str, enlace: str) -> None:
        _ = (correo, enlace)


class FakeTokenRepo:
    def guardar_hash(self, usuario_id: int, token_hash: str, expira_en: datetime) -> None:
        _ = (usuario_id, token_hash, expira_en)

    def validar(self, token_hash: str) -> TokenRecuperacion | None:
        _ = token_hash
        return TokenRecuperacion(usuario_id=1, expira_en=datetime.now(UTC), usado=False)

    def marcar_usado(self, token_hash: str) -> None:
        _ = token_hash


def test_registro_convierte_carrito_anonimo() -> None:
    repo = FakeAuthRepo()
    service = AuthService(
        auth_repo=repo,
        token_repo=FakeTokenRepo(),
        email_sender=FakeEmailSender(),
    )

    service.registrar(
        nombre="Nuevo",
        correo="nuevo@test.com",
        password="password123",
        carrito_anonimo=[ItemCarritoAnonimo(producto_id=10, cantidad=2)],
    )

    assert repo.llamo_convertir


def test_login_sin_carrito_activa_ultimo_editado() -> None:
    repo = FakeAuthRepo()
    service = AuthService(
        auth_repo=repo,
        token_repo=FakeTokenRepo(),
        email_sender=FakeEmailSender(),
    )

    service.login(correo="ana@test.com", password="password123", carrito_anonimo=[])

    assert repo.llamo_activar
