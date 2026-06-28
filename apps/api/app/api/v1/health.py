import logging
from typing import Literal

import psycopg
from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "error"]


def _check_db() -> bool:
    try:
        settings = get_settings()
        with psycopg.connect(settings.database_url) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        logger.warning("Health: DB unreachable", exc_info=True)
        return False


@router.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    db_ok = _check_db()
    if not db_ok:
        response.status_code = 503
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db="ok" if db_ok else "error",
    )
