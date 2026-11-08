from fastapi import APIRouter, Depends, status, Query, Cookie, Body
from fastapi.responses import Response, JSONResponse, RedirectResponse
from typing import Annotated
from datetime import datetime

from app.services.oauth_service import OAuthService, get_service
from common.schemas import CallbackRequest, ResponseCookies


router = APIRouter(prefix="/auth", tags=["auth"])


OAuthServ = Annotated[OAuthService, Depends(get_service)]

callback_request = Annotated[CallbackRequest | None, Query()]
cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]


async def refresh_monitor(service: OAuthServ, resp_cookies: cookies):
    try:
        yield
    finally:
        initial_response_time = datetime.strptime(resp_cookies.response_time, "%H:%M:%S")
        time_diff = datetime.now() - initial_response_time

        if time_diff.seconds >= 3000:
            # QUE HAGO CON LA RESPONSE? SE ENVIA SOLA AL CLIENTE?
            response = service.refresh_token(resp_cookies.refresh_token)


@router.get("/login-url", status_code=status.HTTP_302_FOUND)
def login_url(service: OAuthServ) -> RedirectResponse:
    return service.login_url()

@router.get("/logout-url", status_code=status.HTTP_302_FOUND)
def logout_url(service: OAuthServ) -> RedirectResponse:
    return service.logout_url()

@router.get("/callback")
def callback(service: OAuthServ, request: callback_request = None, req_cookies: cookies = None) -> Response:
    return service.auth_callback(request, req_cookies)

@router.post("/obtain-token", status_code=status.HTTP_200_OK, dependencies=[Depends(refresh_monitor)])
def obtain_token(service: OAuthServ, req_cookies: cookies = None, option: Annotated[str, Body()] = "access") -> Response:
    return service.obtain_tokens(req_cookies, option)