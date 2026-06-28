from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service
from app.api.v1.dependencies import get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Iterator[None]:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@dataclass
class _Usuario:
    id: int
    nombre: str
    correo: str


@dataclass
class _AuthResult:
    usuario: _Usuario
    token: str


class _FakeAuthService:
    def __init__(self) -> None:
        self.fail_mode: str | None = None

    def registrar(self, **_: Any) -> _AuthResult:
        if self.fail_mode == "conflict":
            from app.domain.auth import AuthConflictError

            raise AuthConflictError("El correo ya está registrado")
        return _AuthResult(usuario=_Usuario(id=1, nombre="Ana", correo="ana@test.com"), token="jwt")

    def login(self, **_: Any) -> _AuthResult:
        if self.fail_mode == "unauthorized":
            from app.domain.auth import AuthUnauthorizedError

            raise AuthUnauthorizedError("Credenciales inválidas")
        return _AuthResult(usuario=_Usuario(id=1, nombre="Ana", correo="ana@test.com"), token="jwt")

    async def recuperar(self, **_: Any) -> None:
        return None

    def restablecer(self, **_: Any) -> _AuthResult:
        if self.fail_mode == "bad_request":
            from app.domain.auth import AuthBadRequestError

            raise AuthBadRequestError("El enlace de recuperación es inválido o expiró")
        return _AuthResult(usuario=_Usuario(id=1, nombre="Ana", correo="ana@test.com"), token="jwt")

    def actualizar_perfil(self, **_: Any) -> _Usuario:
        if self.fail_mode == "bad_request":
            from app.domain.auth import AuthBadRequestError

            raise AuthBadRequestError("El nombre debe tener al menos 2 caracteres")
        return _Usuario(id=1, nombre="Nuevo Nombre", correo="ana@test.com")


def test_registro_201() -> None:
    fake = _FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post(
        "/api/v1/auth/registro",
        json={"nombre": "Ana", "correo": "ana@test.com", "password": "password123"},
    )

    assert response.status_code == 201
    assert response.json()["usuario"]["correo"] == "ana@test.com"


def test_registro_409_por_correo_duplicado() -> None:
    fake = _FakeAuthService()
    fake.fail_mode = "conflict"
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post(
        "/api/v1/auth/registro",
        json={"nombre": "Ana", "correo": "ana@test.com", "password": "password123"},
    )

    assert response.status_code == 409


def test_login_401_credenciales_invalidas() -> None:
    fake = _FakeAuthService()
    fake.fail_mode = "unauthorized"
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post(
        "/api/v1/auth/login",
        json={"correo": "ana@test.com", "password": "mala12345"},
    )

    assert response.status_code == 401


def test_login_200_exitoso() -> None:
    fake = _FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post(
        "/api/v1/auth/login",
        json={"correo": "ana@test.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["usuario"]["correo"] == "ana@test.com"
    assert isinstance(response.json()["token"], str)


def test_recuperar_200_siempre() -> None:
    fake = _FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post("/api/v1/auth/recuperar", json={"correo": "sin-registro@test.com"})

    assert response.status_code == 200


def test_restablecer_400_token_invalido() -> None:
    fake = _FakeAuthService()
    fake.fail_mode = "bad_request"
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post(
        "/api/v1/auth/restablecer",
        json={"token": "token-vencido", "nuevaPassword": "password123"},
    )

    assert response.status_code == 400


def test_restablecer_200_exitoso() -> None:
    fake = _FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake

    response = client.post(
        "/api/v1/auth/restablecer",
        json={"token": "token-valido-123", "nuevaPassword": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["usuario"]["correo"] == "ana@test.com"
    assert isinstance(response.json()["token"], str)


def test_logout_401_sin_token() -> None:
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401


def test_logout_204_con_token_valido() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert response.text == ""


def test_actualizar_perfil_401_sin_token() -> None:
    response = client.patch(
        "/api/v1/auth/perfil",
        json={"nombre": "Nuevo Nombre"},
    )

    assert response.status_code == 401


def test_actualizar_perfil_400_nombre_invalido() -> None:
    fake = _FakeAuthService()
    fake.fail_mode = "bad_request"
    app.dependency_overrides[get_auth_service] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }

    response = client.patch(
        "/api/v1/auth/perfil",
        json={"nombre": "A"},
    )

    assert response.status_code == 400


def test_actualizar_perfil_200_exitoso() -> None:
    fake = _FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "correo": "ana@test.com",
        "nombre": "Ana",
    }

    response = client.patch(
        "/api/v1/auth/perfil",
        json={"nombre": "Nuevo Nombre"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Nuevo Nombre"
    assert data["correo"] == "ana@test.com"
    assert data["id"] == 1
