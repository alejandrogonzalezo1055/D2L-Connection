from fastapi import Response, status, Path, Cookie, Body
from functools import lru_cache
from typing import Annotated
import httpx

from common import settings
from common.settings import get_settings
from common.schemas import ResponseCookies, create_response


cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
req_body = Annotated[dict, Body()]
id = Annotated[int, Path()]

TIMEOUT = 10


class InternalService():
    def __init__(self):
        self.settings = get_settings()
        self.d2l_client = httpx.Client()
        self.base_url = self.settings.go_base_url
        self.ca_file = self.settings.ca_file
        self.headers = {"Authorization": f"Bearer {self.settings.internal_api_key.get_secret_value()}"}


    def health(self) -> Response:
        response_data = {
            "status_code": status.HTTP_200_OK,
            "content": {
                "status": "ok",
                "brightspace": settings.brightspace_call
            },
            "cookies": None
        }

        return create_response(response_data)


    def put_user(self, external_id: id, body: req_body) -> Response:
        return


    def put_enrollments(self, external_id: id, body: req_body) -> Response:
        return


    def put_assigment(self, course_external_id: id, body: req_body) -> Response:
        return


    def create_ticket(self, external_id) -> Response:
        return


@lru_cache()
def get_service() -> InternalService:
    return InternalService()