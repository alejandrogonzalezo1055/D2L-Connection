from fastapi import APIRouter, Depends, status, Query, Cookie, Body
from fastapi.responses import Response
from typing import Annotated

from app.services.oauth_service import OAuthService, get_service
from common.schemas import CallbackRequest, ResponseCookies


router = APIRouter(prefix="/auth", tags=["auth"])


OAuthServ = Annotated[OAuthService, Depends(get_service)]

callback_request = Annotated[CallbackRequest | None, Query()]
cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]


# DEVUELVE UNA REDIRECT RESPONSE
@router.get("/login-url", status_code=status.HTTP_302_FOUND)
def login_url(service: OAuthServ) -> Response:
    return service.login_url()

# DEVUELVE UNA REDIRECT RESPONSE
@router.get("/logout-url", status_code=status.HTTP_302_FOUND)
def logout_url(service: OAuthServ) -> Response:
    return service.logout_url()

@router.get("/callback")
def callback(service: OAuthServ, request: callback_request = None, req_cookies: cookies = None) -> Response:
    return service.auth_callback(request, req_cookies)

@router.post("/obtain-token", status_code=status.HTTP_200_OK)
def obtain_token(service: OAuthServ, req_cookies: cookies = None, option: Annotated[str, Body()] = "access") -> Response:
    return service.obtain_tokens(req_cookies, option)