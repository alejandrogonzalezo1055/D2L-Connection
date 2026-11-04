from pydantic import BaseModel, Field, field_validator
from typing import Annotated
from fastapi import status, Cookie
from fastapi.responses import RedirectResponse


class AuthCallbackRequest(BaseModel):
    code: str | None= Field(default=None)
    state: str | None = Field(default=None)

    @field_validator("state")
    @classmethod
    def check_state(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("el state de su peticion no tiene la longitud requerida")
        return value


class CallbackResponse(BaseModel):
    status_code: int = Field(default=status.HTTP_200_OK)
    message: str = Field(default="")


def create_redirect_response(data: dict | None = None) -> RedirectResponse:
    response = RedirectResponse(url=data["url"])
    response.status_code = data["status_code"]
    if data["cookies"] is not None:
        for cookie in data["cookies"]:
            response.set_cookie(
                key=cookie["key"],
                value=cookie["value"],
                httponly=cookie["httponly"],
                samesite=cookie["samesite"],
                max_age=cookie["max_age"]
            )

    return response