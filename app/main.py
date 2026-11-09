from fastapi import APIRouter, FastAPI, Request
from http.cookies import SimpleCookie
from datetime import datetime

from common.errors import register_error_handler
from app.routers import health, oauth_router
from app.services.oauth_service import OAuthService


def create_app() -> FastAPI:
    app = FastAPI(title="D2L Connection",version="1.0.0")

    @app.middleware("http")
    async def middleware(service: OAuthService, request: Request, call_next):
        response = await call_next(request)

        resp_cookies_headers = response.headers.getlist("set-cookie")

        resp_cookies = SimpleCookie()
        for cookie in resp_cookies_headers:
            resp_cookies.load(cookie)

        if "response_time" in resp_cookies:
            response_time = resp_cookies["response_time"].value

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time

            if time_diff.seconds >= 3000:
                response = service.auto_obtain_tokens("refresh", response ,refresh_token=resp_cookies["refresh_token"].value, auth_code=resp_cookies["auth_code"].value)
            elif time_diff.seconds > 3600:
                response = service.auto_obtain_tokens("access", response, refresh_token=resp_cookies["refresh_token"].value, auth_code=resp_cookies["auth_code"].value)

        return response

    register_error_handler(app)
    app.include_router(health.router)
    app.include_router(oauth_router.router)

    api_v1 = APIRouter(prefix="/api/v1")
    app.include_router(api_v1)

    return app