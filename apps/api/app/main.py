import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings


class _FiltroLogHealth(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/v1/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_FiltroLogHealth())


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TFG SEPA API",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.auth_url, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)
    app.state.settings = settings
    return app


app = create_app()
