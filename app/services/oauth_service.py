from fastapi import HTTPException, status, Query, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlencode
import secrets
import httpx

from common.settings import get_settings
from common.schemas import AuthCallbackRequest, CallbackResponse, create_redirect_response


callback_request = Annotated[AuthCallbackRequest, Query()]
oauth_cookie = Annotated[str | None, Cookie()]

class OAuthService:
    def __init__(self):
        self.settings = get_settings()
        self.auth_code = None
        self.token_options = {
            "access": "authorization_code",
            "refresh": "refresh_token"
        }
        with httpx.Client() as client:
            self.d2l_client = client

    def login_url(self) -> RedirectResponse:
        url = "http://" + self.settings.mock_auth_base_url + ":8800/oauth2/auth"
        state = secrets.token_urlsafe(24)

        params = {
            "response_type": "code",
            "client_id": self.settings.app_id,
            "redirect_uri": "http://localhost:9000/auth/callback",
            "scope": self.settings.app_scope,
            "state": state
        }

        response_data = {
            "url": f"{url}?{urlencode(params)}",
            "status_code": status.HTTP_302_FOUND,
            "cookie":{
                "key": "oauth_state",
                "value": state,
                "httponly": True,
                "samesite": "lax",
                "max_age": 300
            }
        }

        return create_redirect_response(response_data)


    def logout_url(self) -> RedirectResponse:
        url = "http://" + self.settings.mock_api_base_url + ":8800/d2l/logout"

        response_data = {
            "url": url,
            "status_code": status.HTTP_302_FOUND,
            "cookie": None
        }

        return create_redirect_response(response_data)


    def auth_callback(self, request: callback_request, oauth_state: oauth_cookie) -> CallbackResponse:
        if not oauth_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La petición no trae cookie o esta ha expirado"
            )

        if request.state != oauth_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado de la petición no coincide con el estado de la cookie"
            )

        self.auth_code = request.code

        return CallbackResponse(message="Se obtuvo el codigo de autorizacion")


    def obtain_token(self, option: str = "refresh") -> RedirectResponse:
        if option in self.token_options:
            url = "http://" + self.settings.mock_api_base_url + ":8800/core/connect/token"

            json_response = self.d2l_client.post(
                url=url,
                auth=(self.settings.app_id, self.settings.app_secret.get_secret_value()),
                data={
                    "grant_type":self.token_options[option],
                    "code": self.auth_code,
                    "redirect_uri": "http://localhost:9000/core/callback"
                }
            ).json()

            response_data = {
                "url": url
            }

            response = create_redirect_response(response_data)
        else:
            response = create_redirect_response()

        return response


    def core_callback(self, option: str = "refresh"):
        match option:
            case "access":
                access_token = response["access_token"]
            case "refresh":
                refresh_token = response["refresh_token"]
            case _:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="El token que quiere obtener no existe"
                )

        return


@lru_cache()
def get_service() -> OAuthService:
    return OAuthService()