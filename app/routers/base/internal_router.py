from fastapi import APIRouter, Depends, Response
from typing import Annotated

from common.schemas import require_internal_key
from app.services.base.internal_service import InternalService, get_service


router = APIRouter(prefix="/internal/v1", dependencies=[Depends(require_internal_key)])


InternalService = Annotated[InternalService, Depends(get_service)]


@router.get("/health")
def health(service: InternalService) -> Response:
    return service.health()