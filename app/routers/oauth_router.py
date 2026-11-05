from typing import Annotated
from fastapi import APIRouter, Depends, status, Query, Cookie, Body
from fastapi.responses import Response, RedirectResponse

from app.services.oauth_service import OAuthService, get_service
from common.schemas import CallbackRequest, CallbackResponse

router = APIRouter(prefix="/auth", tags=["auth"])


OAuthServ = Annotated[OAuthService, Depends(get_service)]
callback_request = Annotated[CallbackRequest | None, Query()]

cookie = Annotated[str | None, Cookie()]

@router.get("/login-url", status_code=status.HTTP_302_FOUND)
def login_url(service: OAuthServ) -> RedirectResponse:
    return service.login_url()

@router.get("/logout-url", status_code=status.HTTP_302_FOUND)
def logout_url(service: OAuthServ) -> RedirectResponse:
    return service.logout_url()

@router.post("/obtain-token", status_code=status.HTTP_200_OK)
def obtain_token(service: OAuthServ, refresh_token: cookie = None, option: Annotated[str, Body(embed=True)] = "access") -> Response:
    return service.obtain_tokens(refresh_token, option)

@router.get("/callback")
def callback(service: OAuthServ, request: callback_request = None, oauth_state: cookie = None) -> CallbackResponse:
    return service.auth_callback(request, oauth_state)