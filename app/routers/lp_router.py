from fastapi import APIRouter, Response, Depends, Cookie
from typing import Annotated

from app.services.lp_service import LPService, get_service
from common.schemas import ResponseCookies, validate_version, lp_version


router = APIRouter(prefix="/lp/{version}", dependencies=[Depends(validate_version)], tags=["Learning Platform"])


LPService = Annotated[LPService, Depends(get_service)]

cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]


@router.get("/users/whoami")
def whoami(service: LPService, access_token: cookie) -> Response:
    return service.whoami(access_token)