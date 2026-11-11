from fastapi import Response, status
from functools import lru_cache

from common.settings import get_settings, brightspace_call
from common.schemas import create_response


class InternalService():
    def __init__(self):
        self.settings = get_settings()


    def health(self) -> Response:
        response_data = {
            "status_code": status.HTTP_200_OK,
            "content": {
                "status": "ok",
                "brightspace": brightspace_call
            },
            "cookies": None
        }

        return create_response(response_data)


@lru_cache()
def get_service() -> InternalService:
    return InternalService()