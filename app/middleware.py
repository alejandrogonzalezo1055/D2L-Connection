from collections import defaultdict

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
        self.req_counter = defaultdict(int)

    async def dispatch(self, request: Request, call_next):
        self.req_counter[f"{request.method}-{request.url.path}"] += 1

        resp_cookies = request.cookies

        response = await call_next(request)

        self.logger.info(f"Endpoint: {request.method}-{request.url.path}. Numero de Req contadas: {self.req_counter[f"{request.method}-{request.url.path}"]}")
        login_limit_resp = self.login_counter(resp_cookies)
        if login_limit_resp:
            response = login_limit_resp
            self.req_counter["GET-/auth/login-url"] = 0


        if "response_time" in resp_cookies.keys():
            response_time = resp_cookies["response_time"]

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time

            if self.token_life - self.token_life*15/100 <= time_diff.seconds < self.token_life:
                response = await self.oauth_service.auto_obtain_tokens("refresh", response=response, refresh_token=resp_cookies["refresh_token"])
            elif time_diff.seconds > self.token_life:
                response = await self.oauth_service.auto_obtain_tokens("access")

        return response


    def login_counter(self, resp_cookies: dict[str,str]) -> Response | None:
        if self.req_counter["GET-/auth/login-url"] > 8:
            if "auth_code" in resp_cookies.keys():
                logout = self.oauth_service.auto_logout()
            else:
                logout = False

            response_data = {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "content": f"Ha intentado iniciar sesion demasiadas veces. Sesion Cerrada: {logout}",
                "cookies": None
            }

            return create_response(response_data)

        return None