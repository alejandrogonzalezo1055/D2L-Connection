from fastapi import APIRouter, Depends, Response, Path, Cookie, Body
from typing import Annotated

from common.schemas import ResponseCookies, require_internal_key
from app.services.base.internal_service import InternalService, get_service


router = APIRouter(prefix="/internal/v1", dependencies=[Depends(require_internal_key)])


InternalService = Annotated[InternalService, Depends(get_service)]

cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
req_body = Annotated[dict, Body()]
id = Annotated[int, Path()]


@router.get("/health")
def health(service: InternalService) -> Response:
    return service.health()


@router.put("/users/{external_id}")
def put_user(service: InternalService, external_id: id, body: req_body) -> Response:
    return service.put_user(external_id, body)


@router.put("/users/{external_id}/enrollments")
def put_enrollments(service: InternalService, external_id: id, body: req_body) -> Response:
    return service.put_enrollments(external_id, body)


@router.put("/courses/{course_external_id}/assignments")
def put_assigment(service: InternalService, course_external_id: id, body: req_body) -> Response:
    return service.put_assigment(course_external_id, body)


@router.put("/session-tickets")
def create_tickets(service: InternalService, external_id) -> Response:
    return service.create_ticket(external_id)