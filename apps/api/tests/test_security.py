from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security
from app.core.security import TokenInvalidoError


def test_password_hash_y_verify() -> None:
    password = "password-segura-123"
    hashed = security.hashear_password(password)

    assert hashed != password
    assert security.verificar_password(password, hashed)
    assert not security.verificar_password("otra", hashed)


def test_jwt_roundtrip() -> None:
    token = security.crear_token_acceso(usuario_id=10, correo="persona@test.com")
    payload = security.decodificar_token_acceso(token)

    assert payload["sub"] == "10"
    assert payload["correo"] == "persona@test.com"


def test_jwt_expirado_lanza_error() -> None:
    expirado = datetime.now(UTC) - timedelta(minutes=1)
    payload = {
        "sub": "99",
        "correo": "expirado@test.com",
        "iat": int((expirado - timedelta(minutes=10)).timestamp()),
        "exp": int(expirado.timestamp()),
    }
    token = jwt.encode(payload, "cambiar-en-produccion", algorithm="HS256")

    with pytest.raises(TokenInvalidoError):
        security.decodificar_token_acceso(token)
