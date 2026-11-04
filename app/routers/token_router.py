from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Annotated

from app.services.oauth_service import OAuthService, get_service


OAuthServ = Annotated[OAuthService, Depends(get_service)]

router = APIRouter(prefix="/core", tags=["core"])

@router.post("/obtain-token")
def obtain_token(service: OAuthServ, option: str = "refresh") -> JSONResponse:
    return service.obtain_token(option)

@router.get("/callback")
def callback(service: OAuthServ):
    return service.core_callback()