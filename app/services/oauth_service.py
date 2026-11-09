from fastapi import HTTPException, status, Query, Cookie
from fastapi.responses import Response, JSONResponse

from functools import lru_cache
from typing import Annotated
from urllib.parse import urlencode
from datetime import datetime
import secrets
import httpx

from common.settings import get_settings
from common.schemas import CallbackRequest, ResponseCookies, TOKEN_LIFE, add_cookies, create_redirect_response, create_response
from common.errors import get_logger


Logger = get_logger().logger

callback_request = Annotated[CallbackRequest | None, Query()]
cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
token_rep = Annotated[tuple[dict,int,datetime] | tuple[None,None,None], "Parametro Necesario"]


class OAuthService:
    def __init__(self):
        self.settings = get_settings()
        self.token_options = {
            "access": "authorization_code",
            "refresh": "refresh_token"
        }
        self.d2l_client = httpx.Client()
        self.async_d2l_client = httpx.AsyncClient()


    def auth_url(self, redirect_uri: str) -> tuple[str, str]:
        url = "http://" + self.settings.mock_auth_base_url + ":8800/oauth2/auth"
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
        url, state = self.auth_url("http://localhost:9000/auth/callback")

        response_data = {
            "url": url,
            "status_code": status.HTTP_302_FOUND,
            "cookies":[
                {
                    "key": "oauth_state",
                    "value": state,
                    "httponly": True,
                    "samesite": "lax",
                    "max_age": 300
                }
            ]
        }

        return create_redirect_response(response_data)


    def logout_url(self) -> Response:
        url = "http://" + self.settings.mock_api_base_url + ":8800/d2l/logout"

        response_data = {
            "url": url,
            "status_code": status.HTTP_302_FOUND,
            "cookies": None
        }

        return create_redirect_response(response_data)


    def auth_callback(self, request: callback_request, req_cookies: cookies) -> Response:
        if not req_cookies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La petición no trae cookies o estas han expirado"
            )

        if not req_cookies.oauth_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La petición no trae estado"
            )

        if request.state != req_cookies.oauth_state:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El estado de la petición no coincide con el estado de la cookie"
            )

        response_data = {
            "status_code": status.HTTP_202_ACCEPTED,
            "content": "Se obtuvo el codigo de autorizacion",
            "cookies": [
                {
                    "key": "auth_code",
                    "value": request.code,
                    "httponly": True,
                    "samesite": "lax",
                    "max_age": 300
                }
            ]
        }


        return create_response(response_data)


    def obtain_tokens(self, req_cookies: cookies, option: str) -> Response:
        if not req_cookies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La petición no trae cookie o esta ha expirado"
            )

        if option not in self.token_options.keys():
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="El token que quiere obtener no existe"
            )

        response = JSONResponse(content=None)
        if option in self.token_options.keys() and req_cookies:
            match option:
                case "access":
                    response = self.access_token(req_cookies.auth_code)
                case "refresh":
                    response = self.refresh_token(req_cookies.refresh_token)

        return response


    def token_req(self, option: str, auth_code: cookie = None, refresh_token: cookie = None) -> token_rep:
        url = "http://" + self.settings.mock_api_base_url + ":8800/core/connect/token"

        match option:
            case "refresh":
                response = self.d2l_client.post(
                    url=url,
                    auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                    data={
                        "grant_type": self.token_options["refresh"],
                        "refresh_token": refresh_token
                    }
                )
                Logger.info("TokenReq-Refresh. Se envio una peticion post al cliente d2l.")

                return response.json(), response.status_code, datetime.now()
            case "access":
                response = self.d2l_client.post(
                    url=url,
                    auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                    data={
                        "grant_type": self.token_options["access"],
                        "code": auth_code,
                        "redirect_uri": "http://localhost:9000/auth/callback"
                    }
                )
                Logger.info("TokenReq-Access. Se envio una peticion post al cliente d2l.")

                return response.json(), response.status_code, datetime.now()

        return None, None, None


    async def auto_token_req(self, option: str, auth_code: cookie = None, refresh_token: cookie = None) -> token_rep:
        url = "http://" + self.settings.mock_api_base_url + ":8800/core/connect/token"

        match option:
            case "refresh":
                response = await self.async_d2l_client.post(
                    url=url,
                    auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                    data={
                        "grant_type": self.token_options["refresh"],
                        "refresh_token": refresh_token
                    }
                )
                Logger.info("TokenReq-Refresh. Se envio una peticion post al cliente d2l.")

                return response.json(), response.status_code, datetime.now()
            case "access":
                response = await self.async_d2l_client.post(
                    url=url,
                    auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                    data={
                        "grant_type": self.token_options["access"],
                        "code": auth_code,
                        "redirect_uri": "http://localhost:9000/auth/callback"
                    }
                )
                Logger.info("TokenReq-Access. Se envio una peticion post al cliente d2l.")

                return response.json(), response.status_code, datetime.now()

        return None, None, None


    def access_token(self, auth_code: cookie) -> Response:
        json_response, resp_status, response_time = self.token_req("access", auth_code=auth_code)

        if "error" not in json_response.keys():
            response_data = {
                "status_code": status.HTTP_202_ACCEPTED,
                "content": {
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
                        "value": response_time.strftime("%H:%M:%S"),
                        "httponly": True,
                        "samesite": "lax",
                        "max_age": json_response["expires_in"] + TOKEN_LIFE*50/100
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


    def refresh_token(self, refresh_token: cookie) -> Response:
        json_response, resp_status, response_time = self.token_req("refresh", refresh_token=refresh_token)

        if "error" not in json_response.keys():
            response_data = {
                "status_code": status.HTTP_202_ACCEPTED,
                "content": {
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
                        "value": response_time.strftime("%H:%M:%S"),
                        "httponly": True,
                        "samesite": "lax",
                        "max_age": json_response["expires_in"] + TOKEN_LIFE*50/100
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


    def auto_obtain_tokens(self, option: str, response: Response | None, resp_cookies: list[dict] = None) -> Response:
        if not response:
            Logger.error(
                f"Auto-ObtainTokens.\n"
                f"HTTP code: {status.HTTP_404_NOT_FOUND}. La respuesta no existe o esta vacia."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La respuesta no existe o esta vacia"
            )

        if not resp_cookies[1]["refresh_token"] and option != "access":
            Logger.error(
                f"Auto-ObtainTokens.\n"
                f"HTTP code: {status.HTTP_404_NOT_FOUND}. No existe el token."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el token"
            )

        match option:
            case "refresh":
                Logger.info(
                    f"Auto-ObtainTokens.\n"
                    f"Se va a obtener el refresh token."
                )
                response = self.auto_refresh_token(response, resp_cookies[1]["refresh_token"])
                Logger.info(
                    f"Auto-ObtainTokens.\n"
                    f"Se obtuvo el refresh token."
                )
            case "access":
                Logger.info(
                    f"Auto-ObtainTokens.\n"
                    f"Se va a obtener el access token."
                )
                response = self.auto_access_token(response)
                Logger.info(
                    f"Auto-ObtainTokens.\n"
                    f"Se obtuvo el access token."
                )

        return response


    async def auto_auth_code(self) -> str | None:
        auth_url, state = self.auth_url("http://localhost:9000/auth/auto-callback")

        auth_code_resp = await self.async_d2l_client.get(
            url=auth_url,
            follow_redirects=False
        )
        Logger.info("Auto-AuthCode. Se envio una peticion GET al cliente d2l.")

        resp_location_header = auth_code_resp.headers.get("location")

        if resp_location_header:
            auth_code_url = httpx.URL(resp_location_header)

            query_params = dict(auth_code_url.params)

            if query_params.get("state") != state:
                Logger.error(
                    f"Auto-AuthCode.\n"
                    f"HTTP code: {status.HTTP_409_CONFLICT}.\n"
                    f"El estado de la respuesta no coincide con el estado de la peticion"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El estado de la respuesta no coincide con el estado de la peticion."
                )

            return query_params.get("code")
        else:
            Logger.error("Auto-AuthCode. No tiene la url de redireccion con el auth_code")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No tiene la url de redireccion con el auth_code"
            )


    def auto_access_token(self, response: Response) -> Response:
        json_response, resp_status, response_time = self.auto_token_req("access", auth_code=self.auto_auth_code())

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
                    "value": response_time.strftime("%H:%M:%S"),
                    "httponly": True,
                    "samesite": "lax",
                    "max_age": json_response["expires_in"] + TOKEN_LIFE*50/100
                }
            ]

            response = add_cookies(response, cookies_data)
            Logger.info("Auto-Access. Se añadieron las tokens con los tokens generados automaticamente")
        else:
            Logger.error(
                f"status_code: {resp_status}\n"
                f"token_type: auto-access\n"
                f"error: {json_response["error"]}\n"
                f"error_description: {json_response["error_description"]}"
            )

        return response


    def auto_refresh_token(self, response: Response, refresh_token: cookie) -> Response:
        json_response, resp_status, response_time = self.auto_token_req("refresh", refresh_token=refresh_token)

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
                    "value": response_time.strftime("%H:%M:%S"),
                    "httponly": True,
                    "samesite": "lax",
                    "max_age": json_response["expires_in"] + TOKEN_LIFE*50/100
                }
            ]

            response = add_cookies(response, cookies_data)
            Logger.info("Auto-Refresh. Se añadieron las tokens con los tokens generados automaticamente")
        else:
            Logger.error(
                f"status_code: {resp_status}\n"
                f"token_type: auto-refresh\n"
                f"error: {json_response["error"]}\n"
                f"error_description: {json_response["error_description"]}"
            )

        return response


@lru_cache()
def get_service() -> OAuthService:
    return OAuthService()