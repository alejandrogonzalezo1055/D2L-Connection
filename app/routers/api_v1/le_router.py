from fastapi import APIRouter, Depends, Cookie
from typing import Annotated

from app.services.api_v1.le_service import LEService, get_service
from common.schemas import ResponseCookies, ProductVersionValidator


router = APIRouter(prefix="/le/{product_version}", dependencies=[Depends(ProductVersionValidator("le"))], tags=["Learning Enviroment"])


LPService = Annotated[LEService, Depends(get_service)]

cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]

# EL OrgUnitID DEBERIA SER ALGO GLOBAL DE MI APP, PUES SOLO SE CONCENTRARA EN ESE CURSO?
# DEBERIA MAS BIEN HACRLO PARA CUALQUIER CURSO?
@router.get("/{OrgUnitID}/dropbox")
def a():
    ...