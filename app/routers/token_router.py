from fastapi import APIRouter, Depends
from fastapi.responses import Response
from typing import Annotated

from app.services.oauth_service import OAuthService, get_service


OAuthServ = Annotated[OAuthService, Depends(get_service)]

router = APIRouter(prefix="/core", tags=["core"])

@router.post("/obtain-token")
def obtain_token(service: OAuthServ, option: str = "refresh") -> Response:
    return service.obtain_tokens(option)

@router.get("/callback")
def callback(service: OAuthServ):
    return service.core_callback()