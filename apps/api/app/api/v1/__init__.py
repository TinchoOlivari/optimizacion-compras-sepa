from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.carritos import router as carritos_router
from app.api.v1.compras_guiadas import router as compras_guiadas_router
from app.api.v1.health import router as health_router
from app.api.v1.preferencias import router as preferencias_router
from app.api.v1.productos import router as productos_router
from app.api.v1.sucursales import router as sucursales_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(productos_router)
router.include_router(carritos_router)
router.include_router(compras_guiadas_router)
router.include_router(preferencias_router)
router.include_router(sucursales_router)
