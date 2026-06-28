from datetime import UTC, datetime

from psycopg.rows import dict_row

from app.domain.ports import (
    IAuthRepository,
    ItemCarritoAnonimo,
    ITokenRepository,
    TokenRecuperacion,
    UsuarioAuth,
)
from app.infra.db import get_connection


class AuthRepository(IAuthRepository, ITokenRepository):
    def crear_usuario(self, nombre: str, correo: str, password_hash: str) -> int:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usuario (nombre, correo, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (nombre, correo, password_hash),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No se pudo crear el usuario")
                conn.commit()
                return int(row[0])

    def obtener_por_correo(self, correo: str) -> UsuarioAuth | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, nombre, correo, password_hash
                    FROM usuario
                    WHERE correo = %s
                    """,
                    (correo,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return UsuarioAuth(
                    id=int(row["id"]),
                    nombre=str(row["nombre"]),
                    correo=str(row["correo"]),
                    password_hash=str(row["password_hash"]),
                )

    def obtener_por_id(self, usuario_id: int) -> UsuarioAuth | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, nombre, correo, password_hash
                    FROM usuario
                    WHERE id = %s
                    """,
                    (usuario_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return UsuarioAuth(
                    id=int(row["id"]),
                    nombre=str(row["nombre"]),
                    correo=str(row["correo"]),
                    password_hash=str(row["password_hash"]),
                )

    def actualizar_password(self, usuario_id: int, password_hash: str) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE usuario SET password_hash = %s WHERE id = %s",
                    (password_hash, usuario_id),
                )
                conn.commit()

    def convertir_carrito_anonimo(self, usuario_id: int, items: list[ItemCarritoAnonimo]) -> None:
        if not items:
            self.activar_ultimo_carrito(usuario_id)
            return

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE carrito SET activo = false WHERE usuario_id = %s AND activo = true",
                    (usuario_id,),
                )
                cur.execute(
                    """
                    INSERT INTO carrito (usuario_id, titulo, activo)
                    VALUES (%s, NULL, true)
                    RETURNING id
                    """,
                    (usuario_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No se pudo crear el carrito")
                carrito_id = int(row[0])
                for item in items:
                    cur.execute(
                        """
                        INSERT INTO item_carrito (carrito_id, producto_id, cantidad)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (carrito_id, producto_id)
                        DO UPDATE SET cantidad = EXCLUDED.cantidad
                        """,
                        (carrito_id, item.producto_id, item.cantidad),
                    )
                conn.commit()

    def activar_ultimo_carrito(self, usuario_id: int) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE carrito SET activo = false WHERE usuario_id = %s AND activo = true",
                    (usuario_id,),
                )
                cur.execute(
                    """
                    UPDATE carrito
                    SET activo = true
                    WHERE id = (
                        SELECT id
                        FROM carrito
                        WHERE usuario_id = %s
                        ORDER BY fecha_ultima_edicion DESC
                        LIMIT 1
                    )
                    """,
                    (usuario_id,),
                )
                conn.commit()

    def actualizar_nombre(self, usuario_id: int, nombre: str) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE usuario SET nombre = %s WHERE id = %s",
                    (nombre, usuario_id),
                )
                conn.commit()

    def guardar_hash(self, usuario_id: int, token_hash: str, expira_en: datetime) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO token_recuperacion (usuario_id, token_hash, expira_en, usado)
                    VALUES (%s, %s, %s, false)
                    ON CONFLICT (token_hash)
                    DO UPDATE SET usuario_id = EXCLUDED.usuario_id,
                                  expira_en = EXCLUDED.expira_en,
                                  usado = false,
                                  fecha_uso = NULL
                    """,
                    (usuario_id, token_hash, expira_en),
                )
                conn.commit()

    def validar(self, token_hash: str) -> TokenRecuperacion | None:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT usuario_id, expira_en, usado
                    FROM token_recuperacion
                    WHERE token_hash = %s
                    """,
                    (token_hash,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                expira_en_raw = row["expira_en"]
                if not isinstance(expira_en_raw, datetime):
                    return None

                if bool(row["usado"]) or expira_en_raw <= datetime.now(UTC):
                    return None

                return TokenRecuperacion(
                    usuario_id=int(row["usuario_id"]),
                    expira_en=expira_en_raw,
                    usado=bool(row["usado"]),
                )

    def marcar_usado(self, token_hash: str) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE token_recuperacion
                    SET usado = true,
                        fecha_uso = now()
                    WHERE token_hash = %s
                    """,
                    (token_hash,),
                )
                conn.commit()
