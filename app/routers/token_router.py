from fastapi import APIRouter, Depends, Body, status, Cookie
from fastapi.responses import Response
from typing import Annotated

from app.services.oauth_service import OAuthService, get_service


router = APIRouter(prefix="/core", tags=["core"])

OAuthServ = Annotated[OAuthService, Depends(get_service)]
cookie = Annotated[str | None, Cookie()]

@router.post("/obtain-token", status_code=status.HTTP_200_OK)
def obtain_token(service: OAuthServ, option: Annotated[str, Body()] = "refresh") -> Response:
    return service.obtain_tokens(option)

@router.get("/callback")
def callback(service: OAuthServ):
    return service.core_callback()