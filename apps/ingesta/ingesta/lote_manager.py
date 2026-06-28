from __future__ import annotations

from datetime import date
from typing import Any

import psycopg
from psycopg.types.json import Json


class LoteManager:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def begin(self, fecha_lote: date, origen: str) -> int:
        with self.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lote_ingesta (
                    fecha_lote,
                    origen,
                    estado,
                    archivos_procesados,
                    archivos_con_error,
                    detalle_errores,
                    fecha_ejecucion
                )
                VALUES (%s, %s, 'EN_PROCESO', 0, 0, '[]'::jsonb, now())
                ON CONFLICT (fecha_lote, origen)
                DO UPDATE
                SET
                    estado = 'EN_PROCESO',
                    archivos_procesados = 0,
                    archivos_con_error = 0,
                    detalle_errores = '[]'::jsonb,
                    fecha_ejecucion = now()
                RETURNING id
                """,
                (fecha_lote, origen),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("No fue posible crear/abrir lote_ingesta")
            return int(row[0])

    def create_savepoint(self, name: str) -> None:
        with self.connection.cursor() as cur:
            cur.execute(f"SAVEPOINT {name}")

    def rollback_to_savepoint(self, name: str) -> None:
        with self.connection.cursor() as cur:
            cur.execute(f"ROLLBACK TO SAVEPOINT {name}")

    def release_savepoint(self, name: str) -> None:
        with self.connection.cursor() as cur:
            cur.execute(f"RELEASE SAVEPOINT {name}")

    def finalize(
        self,
        lote_id: int,
        archivos_procesados: int,
        archivos_con_error: int,
        detalle_errores: list[dict[str, str]],
    ) -> str:
        if archivos_con_error == 0:
            estado = "PROCESADO"
        elif archivos_procesados > 0:
            estado = "PARCIAL"
        else:
            estado = "ERROR"

        with self.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE lote_ingesta
                SET
                    estado = %s,
                    archivos_procesados = %s,
                    archivos_con_error = %s,
                    detalle_errores = %s,
                    fecha_ejecucion = now()
                WHERE id = %s
                """,
                (
                    estado,
                    archivos_procesados,
                    archivos_con_error,
                    Json(detalle_errores),
                    lote_id,
                ),
            )

        return estado


def build_error(phase: str, error: Exception) -> dict[str, str]:
    return {
        "phase": phase,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def safe_error_payload(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            normalized = {str(key): str(raw) for key, raw in item.items()}
            output.append(normalized)
    return output
