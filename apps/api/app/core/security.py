from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import cast

import bcrypt
import jwt
from jwt import ExpiredSignatureError
from jwt import InvalidTokenError as JwtInvalidTokenError

from app.core.config import get_settings

ALGORITMO_JWT = "HS256"


class TokenInvalidoError(Exception):
    pass


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password_plano.encode("utf-8"), password_hash.encode("utf-8"))


def crear_token_acceso(usuario_id: int, correo: str) -> str:
    settings = get_settings()
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {
        "sub": str(usuario_id),
        "correo": correo,
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
    }
    return jwt.encode(payload, settings.api_jwt_secret, algorithm=ALGORITMO_JWT)


def decodificar_token_acceso(token: str) -> dict[str, str | int]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.api_jwt_secret, algorithms=[ALGORITMO_JWT])
    except ExpiredSignatureError as error:
        raise TokenInvalidoError("El token expiró") from error
    except JwtInvalidTokenError as error:
        raise TokenInvalidoError("Token inválido") from error

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise TokenInvalidoError("Token inválido")

    return cast(dict[str, str | int], payload)


def generar_token_recuperacion() -> str:
    return token_urlsafe(32)


def hashear_token_recuperacion(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
