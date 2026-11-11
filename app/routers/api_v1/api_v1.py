from fastapi import APIRouter

from app.routers.api_v1 import lp_router, le_router

router = APIRouter(prefix="/api/v1")

router.include_router(le_router.router)
router.include_router(lp_router.router)

