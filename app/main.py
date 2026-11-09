from fastapi import APIRouter, FastAPI, Request
from http.cookies import SimpleCookie
from datetime import datetime

from app.routers.oauth_router import OAuthServ
from common.errors import register_error_handler
from app.routers import health, oauth_router


TOKEN_LIFE = 3600


def create_app() -> FastAPI:
    app = FastAPI(title="D2L Connection",version="1.0.0")

    @app.middleware("http")
    async def middleware(request: Request, call_next):
        response = await call_next(request)

        resp_cookies_headers = response.headers.getlist("set-cookie")

        resp_cookies = SimpleCookie()
        for cookie in resp_cookies_headers:
            resp_cookies.load(cookie)

        if "response_time" in resp_cookies:
            response_time = resp_cookies["response_time"].value

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time

            if TOKEN_LIFE - TOKEN_LIFE*20/100 <= time_diff.seconds < TOKEN_LIFE:
                response = OAuthServ.auto_obtain_tokens("refresh", response ,refresh_token=resp_cookies["refresh_token"].value)
            elif time_diff.seconds > TOKEN_LIFE:
                response = OAuthServ.auto_obtain_tokens("access", response)

        return response

    register_error_handler(app)
    app.include_router(health.router)
    app.include_router(oauth_router.router)

    api_v1 = APIRouter(prefix="/api/v1")
    app.include_router(api_v1)

    return app