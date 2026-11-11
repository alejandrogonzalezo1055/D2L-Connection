from fastapi import FastAPI

from common.errors import register_error_handler
from app.routers.base import health, oauth_router, internal_router
from app.routers.api_v1 import api_v1
from app.middleware import Middleware


def create_app() -> FastAPI:
    app = FastAPI(title="D2L Connection",version="1.0.0")

    register_error_handler(app)
    app.include_router(health.router)
    app.include_router(oauth_router.router)
    app.include_router(internal_router.router)

    app.include_router(api_v1.router)

    app.add_middleware(Middleware)

    return app