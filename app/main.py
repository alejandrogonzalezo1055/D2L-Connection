from fastapi import APIRouter, FastAPI, Request
from http.cookies import SimpleCookie
from datetime import datetime
import asyncio

from app.routers import health, oauth_router
from app.services.oauth_service import get_service
from common.errors import register_error_handler
from common.schemas import TOKEN_LIFE


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
        response = await call_next(request)

        resp_cookies_headers = response.headers.getlist("set-cookie")

        resp_cookies = SimpleCookie()
        for cookie in resp_cookies_headers:
            resp_cookies.load(cookie)

        if "response_time" in resp_cookies:
            response_time = resp_cookies["response_time"].value

            rep_cookies = [
                {"response_time": response_time},
                {"refresh_token": resp_cookies["refresh_token"].value},
                {"":""}
            ]

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time

            if TOKEN_LIFE - TOKEN_LIFE * 15 / 100 <= time_diff.seconds < TOKEN_LIFE:
                response = OAuthServ.auto_obtain_tokens("refresh", response, resp_cookies=rep_cookies)
            elif time_diff.seconds > TOKEN_LIFE:
                response = OAuthServ.auto_obtain_tokens("access", response)

        return response

    return app