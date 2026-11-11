from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, status
from datetime import datetime

from common.errors import Logger
from common.settings import TOKEN_LIFE
from common.schemas import create_response
from app.services.oauth_service import get_service


class Middleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.oauth_service = get_service()
        self.logger = Logger().logger
        self.token_life = TOKEN_LIFE
        self.req_counter = {}

    async def dispatch(self, request: Request, call_next):
        self.req_counter[f"{request.method}-{request.url.path}"] += 1
        resp_cookies = request.cookies

        response = await call_next(request)

        if "response_time" in resp_cookies.keys():
            response_time = resp_cookies["response_time"]

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time

            if time_diff.seconds < self.token_life:
                resp_login_counter = self.login_counter()
                if resp_login_counter:
                    response = resp_login_counter
            elif self.token_life - self.token_life * 15 / 100 <= time_diff.seconds < self.token_life:
                resp_login_counter = self.login_counter()
                if not resp_login_counter:
                    response = await self.oauth_service.auto_obtain_tokens("refresh", response=response, refresh_token=resp_cookies["refresh_token"])
                else:
                    response = resp_login_counter
            elif time_diff.seconds > self.token_life:
                response = await self.oauth_service.auto_obtain_tokens("access")

        return response


    def login_counter(self) -> Response | None:
        if self.req_counter["GET-/auth/login-url"] > 8:
            response_data = {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "content": "Ha intentado iniciar sesion demasiadas veces",
                "cookies": None
            }

            return create_response(response_data)

        return None