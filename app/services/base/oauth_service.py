from fastapi import HTTPException, status, Query, Cookie, Request
from fastapi.responses import Response, JSONResponse

from functools import lru_cache
from typing import Annotated
from urllib.parse import urlencode
from datetime import datetime
import secrets
import httpx

from common import settings
from common.settings import get_settings, TOKEN_LIFE
from common.schemas import CallbackRequest, ResponseCookies
from common.schemas import add_cookies, delete_cookies, create_redirect_response, create_response
from common.errors import get_logger


callback_request = Annotated[CallbackRequest | None, Query()]
cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
token_rep = Annotated[tuple[dict,int,str] | None | bool, "Parametro Necesario"]


time_format = "%Y-%m-%d %H:%M:%S"


class OAuthService:
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger().logger
        self.token_options = {
            "access": "authorization_code",
            "refresh": "refresh_token"
        }
        self.httpx_client = httpx.Client()
        self.async_httpx_client = httpx.AsyncClient()
        self.callback_url = "https://localhost:9000/auth/callback"


    def auth_url(self, redirect_uri: str) -> tuple[str, str]:
        url = self.settings.get_oauth_url()
        state = secrets.token_urlsafe(24)

        params = {
            "response_type": "code",
            "client_id": self.settings.app_id,
            "redirect_uri": redirect_uri,
            "scope": self.settings.app_scope,
            "state": state
        }

        return f"{url}?{urlencode(params)}", state


    def login_url(self) -> Response:
        url, state = self.auth_url(self.callback_url)

        response_data = {
            "url": url,
            "status_code": status.HTTP_302_FOUND,
            "cookies":[
                {
                    "key": "oauth_state",
                    "value": state,
                    "httponly": True,
                    "samesite": "lax",
                    "max_age": TOKEN_LIFE*8.5/100
                }
            ]
        }

        return create_redirect_response(response_data)


    def logout_url(self) -> Response:
        url = self.settings.get_api_url(2) + "/logout"

        response_data = {
            "url": url,
            "status_code": status.HTTP_302_FOUND,
            "cookies": None
        }

        return delete_cookies(create_redirect_response(response_data))


    def auth_callback(self, request: callback_request, req_cookies: cookies) -> Response:
        if request.error == "access_denied":
            response_data = {
                "url": self.settings.frontend_url + "/login?error=access_denied",
                "status_code": status.HTTP_302_FOUND,
                "cookies": None
            }

            return delete_cookies(create_redirect_response(response_data))
        else:
            if not req_cookies:
                response_data = {
                    "url": self.settings.frontend_url + "/login?error=session_expired",
                    "status_code": status.HTTP_302_FOUND,
                    "cookies": None
                }

                return create_redirect_response(response_data)

            if not req_cookies.oauth_state:
                response_data = {
                    "url": self.settings.frontend_url + "/login?error=session_expired",
                    "status_code": status.HTTP_302_FOUND,
                    "cookies": None
                }

                return create_redirect_response(response_data)

            if request.state != req_cookies.oauth_state:
                response_data = {
                    "url": self.settings.frontend_url + "/login?error=session_expired",
                    "status_code": status.HTTP_302_FOUND,
                    "cookies": None
                }

                return create_redirect_response(response_data)
            else:
                response = self.access_token(request.code, False)

        return response


    def obtain_tokens(self, req_cookies: cookies, option: dict[str, str | bool]) -> Response:
        if not req_cookies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La petición no trae cookie o esta ha expirado"
            )

        if option.get("token") not in self.token_options.keys():
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="El token que quiere obtener no existe"
            )

        response = JSONResponse(content=None)
        if req_cookies.auth_code or req_cookies.refresh_token:
            match option.get("token"):
                case "access":
                    response = self.access_token(req_cookies.auth_code, option.get("manual"))
                case "refresh":
                    response = self.refresh_token(req_cookies.refresh_token, option.get("manual"))
        elif not req_cookies.auth_code:
            response_data = {
                "status_code": status.HTTP_406_NOT_ACCEPTABLE,
                "content": "La peticion no trae auth_code",
                "cookies": None
            }

            return create_response(response_data)
        elif not req_cookies.refresh_token:
            response_data = {
                "status_code": status.HTTP_406_NOT_ACCEPTABLE,
                "content": "La peticion no trae refresh_token",
                "cookies": None
            }

            return create_response(response_data)

        return response


    def token_req(self, option: str, auth_code: cookie = None, refresh_token: cookie = None) -> token_rep:
        url = self.settings.get_token_url()

        match option:
            case "refresh":
                response = self.httpx_client.post(
                    url=url,
                    auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                    data={
                        "grant_type": self.token_options["refresh"],
                        "refresh_token": refresh_token
                    }
                )
                self.logger.info("TokenReq-Refresh. Se envio una peticion post al cliente d2l.")

                if response.is_success:
                    return response.json(), response.status_code, datetime.now().isoformat()
                else:
                    settings.brightspace_call = False

                    return settings.brightspace_call
            case "access":
                response = self.httpx_client.post(
                    url=url,
                    auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                    data={
                        "grant_type": self.token_options["access"],
                        "code": auth_code,
                        "redirect_uri": self.callback_url
                    }
                )
                self.logger.info("TokenReq-Access. Se envio una peticion post al cliente d2l.")

                if response.is_success:
                    return response.json(), response.status_code, datetime.now().isoformat()
                else:
                    settings.brightspace_call = False

                    return settings.brightspace_call

        return None


    def access_token(self, auth_code: cookie, manual: bool) -> Response:
        token_reply = self.token_req("access", auth_code=auth_code)

        if token_reply == False:
            response = Response()

            if not manual:
                response_data = {
                    "url": self.settings.frontend_url + "/login?error=access_denied",
                    "status_code": status.HTTP_302_FOUND,
                    "cookies": None
                }

                response = create_redirect_response(response_data)
            else:
                response_data = {
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "content": "La peticion a brightspace fallo.",
                    "cookies": None
                }

                response = create_response(response_data)

            return response
        else:
            json_response, resp_status, response_time = token_reply

            if "error" not in json_response.keys():
                response_data = {
                    "status_code": status.HTTP_202_ACCEPTED,
                    "content": {
                        "message": "Se obtuvo el codigo de acceso, a continuacion unos detalles.",
                        "token_type": json_response["token_type"],
                        "expires_in": json_response["expires_in"],
                        "scope": json_response["scope"]
                    },
                    "cookies": [
                        {
                            "key": "access_token",
                            "value": json_response["access_token"],
                            "httponly": True,
                            "samesite": "lax",
                            "max_age": json_response["expires_in"]
                        },
                        {
                            "key": "refresh_token",
                            "value": json_response["refresh_token"],
                            "httponly": True,
                            "samesite": "lax",
                            "max_age": json_response["expires_in"]
                        },
                        {
                            "key": "response_time",
                            "value": response_time,
                            "httponly": True,
                            "samesite": "lax",
                            "max_age": json_response["expires_in"]
                        }
                    ]
                }
            else:
                response_data = {
                    "status_code": resp_status,
                    "content": {
                        "token_type":"access",
                        "error": json_response["error"],
                        "error_description": json_response["error_description"]
                    },
                    "cookies": None
                }

            return create_response(response_data)


    def refresh_token(self, refresh_token: cookie, manual: bool) -> Response:
        token_reply = self.token_req("refresh", refresh_token=refresh_token)

        if token_reply == False:
            response = Response()

            if not manual:
                response_data = {
                    "url": self.settings.frontend_url + "/login?error=access_denied",
                    "status_code": status.HTTP_302_FOUND,
                    "cookies": None
                }

                response = create_redirect_response(response_data)
            else:
                response_data = {
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "content": "La peticion a brightspace fallo.",
                    "cookies": None
                }

                response = create_response(response_data)

            return response
        else:
            json_response, resp_status, response_time = token_reply

            if "error" not in json_response.keys():
                response_data = {
                    "status_code": status.HTTP_202_ACCEPTED,
                    "content": {
                        "message": "Se obtuvo el codigo de acceso, a continuacion unos detalles.",
                        "token_type": json_response["token_type"],
                        "expires_in": json_response["expires_in"],
                        "scope": json_response["scope"]
                    },
                    "cookies": [
                        {
                            "key": "access_token",
                            "value": json_response["access_token"],
                            "httponly": True,
                            "samesite": "lax",
                            "max_age": json_response["expires_in"]
                        },
                        {
                            "key": "refresh_token",
                            "value": json_response["refresh_token"],
                            "httponly": True,
                            "samesite": "lax",
                            "max_age": json_response["expires_in"]
                        },
                        {
                            "key": "response_time",
                            "value": response_time,
                            "httponly": True,
                            "samesite": "lax",
                            "max_age": json_response["expires_in"]
                        }
                    ]
                }
            else:
                response_data = {
                    "status_code": resp_status,
                    "content": {
                        "token_type": "refresh",
                        "error": json_response["error"],
                        "error_description": json_response["error_description"]
                    },
                    "cookies": None
                }

            return create_response(response_data)


    async def auto_obtain_tokens(self, option: dict[str, str | bool], response: Response | None = None, refresh_token: cookie = None) -> Response:
        if not response and option.get("token") != "access":
            self.logger.error(
                f"Auto-ObtainTokens.\n"
                f"HTTP code: {status.HTTP_404_NOT_FOUND}. La respuesta no existe o esta vacia."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La respuesta no existe o esta vacia"
            )

        if not refresh_token and option.get("token") != "access":
            self.logger.error(
                f"Auto-ObtainTokens.\n"
                f"HTTP code: {status.HTTP_404_NOT_FOUND}. No existe el refresh token o ya caduco."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el token"
            )

        match option.get("token"):
            case "refresh":
                self.logger.info(f"Auto-ObtainTokens.\nSe va a obtener el refresh token.")
                response = await self.auto_refresh_token(response, refresh_token, True)
                self.logger.info(f"Auto-ObtainTokens.\nSe obtuvo el refresh token.")
            case "access":
                self.logger.info(f"Auto-ObtainTokens.\nSe va a devolver un 408")
                response_data = {
                    "status_code": status.HTTP_408_REQUEST_TIMEOUT,
                    "content": "Su token de refresco expiro, vuelva a obtener el auth_code y el access token",
                    "cookies": None
                }
                response = delete_cookies(create_response(response_data))

        return response


    async def auto_token_req(self, refresh_token: cookie = None) -> token_rep:
        url = self.settings.get_token_url()

        response = await self.async_httpx_client.post(
            url=url,
            auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
            data={
                "grant_type": self.token_options["refresh"],
                "refresh_token": refresh_token
            }
        )
        self.logger.info("TokenReq-Refresh. Se envio una peticion post al cliente d2l.")

        if response.is_success:
            return response.json(), response.status_code, datetime.now().isoformat()
        else:
            settings.brightspace_call = False

            return settings.brightspace_call


    async def auto_refresh_token(self, response: Response, refresh_token: cookie, manual: bool) -> Response:
        token_reply = await self.auto_token_req(refresh_token=refresh_token)

        if token_reply == False:
            response = Response()

            if not manual:
                response_data = {
                    "url": self.settings.frontend_url + "/login?error=access_denied",
                    "status_code": status.HTTP_302_FOUND,
                    "cookies": None
                }

                response = create_redirect_response(response_data)
            else:
                response_data = {
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "content": "La peticion a brightspace fallo.",
                    "cookies": None
                }

                response = create_response(response_data)

            return response
        else:
            json_response, resp_status, response_time = token_reply

            if json_response and "error" not in json_response.keys():
                cookies_data = [
                    {
                        "key": "access_token",
                        "value": json_response["access_token"],
                        "httponly": True,
                        "samesite": "lax",
                        "max_age": json_response["expires_in"]
                    },
                    {
                        "key": "refresh_token",
                        "value": json_response["refresh_token"],
                        "httponly": True,
                        "samesite": "lax",
                        "max_age": json_response["expires_in"]
                    },
                    {
                        "key": "response_time",
                        "value": response_time,
                        "httponly": True,
                        "samesite": "lax",
                        "max_age": json_response["expires_in"]
                    }
                ]

                response = add_cookies(response, cookies_data)
                self.logger.info("Auto-Refresh. Se añadieron las tokens con los tokens generados automaticamente")
            else:
                self.logger.error(
                    f"status_code: {resp_status}\n"
                    f"token_type: auto-refresh\n"
                    f"error: {json_response["error"]}\n"
                    f"error_description: {json_response["error_description"]}"
                )

            return response


@lru_cache()
def get_service() -> OAuthService:
    return OAuthService()