from typing import Annotated
from fastapi import APIRouter, Depends, status, Query, Cookie
from fastapi.responses import RedirectResponse

from app.services.oauth_service import OAuthService, get_service
from common.schemas import AuthCallbackRequest, CallbackResponse

router = APIRouter(prefix="/auth", tags=["auth"])


OAuthServ = Annotated[OAuthService, Depends(get_service)]
callback_request = Annotated[AuthCallbackRequest, Query()]

oauth_cookie = Annotated[str | None, Cookie()]

@router.get("/login-url", status_code=status.HTTP_302_FOUND)
def login_url(service: OAuthServ) -> RedirectResponse:
    return service.login_url()

@router.get("/logout-url", status_code=status.HTTP_302_FOUND)
def logout_url(service: OAuthServ) -> RedirectResponse:
    return service.logout_url()

@router.get("/callback")
def callback(service: OAuthServ, request: callback_request, oauth_state: oauth_cookie) -> CallbackResponse:
    return service.auth_callback(request, oauth_state)