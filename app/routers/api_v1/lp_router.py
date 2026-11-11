from fastapi import APIRouter, Response, Depends, Cookie, Path
from typing import Annotated

from app.services.api_v1.lp_service import LPService, get_service
from common.schemas import ResponseCookies, ProductVersionValidator


router = APIRouter(prefix="/lp/{product_version}", dependencies=[Depends(ProductVersionValidator("lp"))], tags=["Learning Platform"])


LPService = Annotated[LPService, Depends(get_service)]

cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
profile_id = Annotated[str, Path()]


@router.get("/users/whoami")
def whoami(service: LPService, access_token: cookie) -> Response:
    return service.whoami(access_token)

# NO TENGO PERMISOS
@router.get("/profiles/{ProfileIdentifier}")
def my_profile(service: LPService, ProfileIdentifier: profile_id, access_token: cookie) -> Response:
    return service.my_profile(ProfileIdentifier, access_token)

@router.get("/enrollments/myenrollments/")
def my_enrollments(service: LPService, access_token: cookie) -> Response:
    return service.myenrollments(access_token)