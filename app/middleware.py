import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, status
from datetime import datetime

from common.errors import Logger
from common.settings import TOKEN_LIFE
from common.schemas import delete_cookies, create_response
from app.services.base.oauth_service import get_service


LIM_INTENTOS_LOGIN = 8
VENTANA_LOGIN = 300
BLOQUEO_LOGIN = VENTANA_LOGIN*2


class Middleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.oauth_service = get_service()
        self.logger = Logger().logger
        self.token_life = TOKEN_LIFE
        self.req_counter: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.ultima_limpieza = time.monotonic()


    async def dispatch(self, request: Request, call_next):
        self.limpiar_counter()

        req_cookies = request.cookies

        login_limit_resp = self.login_counter(request.client.host, request.url.path)
        if login_limit_resp:
            return delete_cookies(login_limit_resp)

        response = await call_next(request)

        if "/auth/" not in request.url.path and "response_time" in req_cookies.keys():
            response_time = req_cookies["response_time"]

            initial_response_time = datetime.strptime(response_time, "%H:%M:%S")
            time_diff = datetime.now() - initial_response_time
            lim_inf = self.token_life - self.token_life*15/100

            if lim_inf <= time_diff.seconds < self.token_life and "refresh_token" in req_cookies.keys():
                response = await self.oauth_service.auto_obtain_tokens("refresh", response=response, refresh_token=req_cookies["refresh_token"])
            elif time_diff.seconds > self.token_life:
                response = await self.oauth_service.auto_obtain_tokens("access")

        return response


    def login_counter(self, client_ip: str, endpoint: str) -> Response | None:
        if endpoint == "/auth/login-url" and self.req_counter[client_ip]["intentos"] == 0:
            self.req_counter[client_ip]["inicio_ventana"] = time.monotonic()
            self.req_counter[client_ip]["intentos"] += 1
        elif endpoint == "/auth/login-url":
            ahora = time.monotonic()
            inicio_ventana = self.req_counter[client_ip]["inicio_ventana"]
            bloqueado_hasta = self.req_counter[client_ip]["bloqueado_hasta"]

            if bloqueado_hasta > ahora:
                response_data = {
                    "status_code": status.HTTP_408_REQUEST_TIMEOUT,
                    "content": f"Debe esperar {bloqueado_hasta - ahora:.2f} segundos para volver a iniciar sesion",
                    "cookies": None
                }

                return create_response(response_data)

            if ahora - inicio_ventana > VENTANA_LOGIN:
                self.req_counter[client_ip]["inicio_ventana"] = ahora
                self.req_counter[client_ip]["intentos"] = 0

            self.req_counter[client_ip]["intentos"] += 1
            intentos = self.req_counter[client_ip]["intentos"]

            if intentos > LIM_INTENTOS_LOGIN:
                self.req_counter[client_ip]["bloqueado_hasta"] = ahora + BLOQUEO_LOGIN

                response_data = {
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                    "content": "Ha intentado iniciar sesion muchas veces",
                    "cookies": None
                }

                return create_response(response_data)

            return None


    def limpiar_counter(self):
        ahora = time.monotonic()

        if ahora - self.ultima_limpieza > 60:
            for ip, datos in list(self.req_counter.items()):
                if datos["bloqueado_hasta"] <= ahora and ahora - datos["inicio_ventana"] > VENTANA_LOGIN:
                    del self.req_counter[ip]

            self.ultima_limpieza = ahora

        return