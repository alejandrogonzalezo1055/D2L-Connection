from fastapi import APIRouter, FastAPI, Request, status
from http.cookies import SimpleCookie
from datetime import datetime
import asyncio

from app.routers import health, oauth_router
from app.services.oauth_service import get_service
from common.errors import register_error_handler
from common.schemas import TOKEN_LIFE, create_response


OAuthServ = get_service()


def create_app() -> FastAPI:
    app = FastAPI(title="D2L Connection",version="1.0.0")

    register_error_handler(app)
    app.include_router(health.router)
    app.include_router(oauth_router.router)

    api_v1 = APIRouter(prefix="/api/v1")
    app.include_router(api_v1)

    @app.middleware("http")
    async def middleware(request: Request, call_next):
        resp_cookies = request.cookies

        response = await call_next(request)

        if "response_time" in resp_cookies.keys():
            response_time = resp_cookies["response_time"]

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time

            if TOKEN_LIFE - TOKEN_LIFE * 15 / 100 <= time_diff.seconds < TOKEN_LIFE:
                response = OAuthServ.auto_obtain_tokens("refresh", response, refresh_token=resp_cookies["refresh_token"])
            elif time_diff.seconds > TOKEN_LIFE:
                response = OAuthServ.auto_obtain_tokens("access")

        return response

    return app