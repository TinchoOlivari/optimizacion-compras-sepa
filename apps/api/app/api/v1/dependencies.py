from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import TokenInvalidoError, decodificar_token_acceso
from app.infra.auth_repo import AuthRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, int | str]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"codigo": "NO_AUTENTICADO", "mensaje": "Se requiere autenticación."}},
        )

    try:
        payload = decodificar_token_acceso(credentials.credentials)
    except TokenInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"codigo": "TOKEN_INVALIDO", "mensaje": str(error)}},
        ) from error

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"codigo": "TOKEN_INVALIDO", "mensaje": "Token inválido."}},
        )

    repo = AuthRepository()
    usuario = repo.obtener_por_id(int(sub))
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"codigo": "TOKEN_INVALIDO", "mensaje": "Usuario no encontrado."}},
        )

    return {"id": usuario.id, "correo": usuario.correo, "nombre": usuario.nombre}
