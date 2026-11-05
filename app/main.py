import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, FastAPI
from common.errors import register_error_handler
from app.routers import health, oauth_router


def create_app() -> FastAPI:
    app = FastAPI(title="D2L Connection",version="1.0.0")

    register_error_handler(app)
    app.include_router(health.router)
    app.include_router(oauth_router.router)

    api_v1 = APIRouter(prefix="/api/v1")
    app.include_router(api_v1)

    return app