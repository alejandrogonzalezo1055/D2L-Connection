from pydantic import BaseModel, field_validator
from fastapi.responses import Response, RedirectResponse, JSONResponse


# es para query params
class CallbackRequest(BaseModel):
    code: str | None = None
    state: str | None = None

    @field_validator("state")
    @classmethod
    def check_state(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("El state de su peticion no tiene la longitud requerida")
        return value


class ResponseCookies(BaseModel):
    auth_code: str | None = None
    oauth_state: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    response_time: str = None


def add_cookies(response: Response, cookies_data: list[dict]) -> Response:
    for cookie in cookies_data:
        response.set_cookie(
            key=cookie["key"],
            value=cookie["value"],
            httponly=cookie["httponly"],
            samesite=cookie["samesite"],
            max_age=cookie["max_age"]
        )

    return response


def create_redirect_response(data: dict | None = None) -> Response:
    response = RedirectResponse(url=data["url"], status_code=data["status_code"])

    if data["cookies"] is not None:
        response = add_cookies(response, data["cookies"])

    return response


def create_response(data: dict | None = None) -> Response:
    response = Response()

    if type(data["content"]) is str:
        response = Response(content=data["content"], status_code=data["status_code"])
    elif type(data["content"]) is dict:
        response = JSONResponse(content=data["content"], status_code=data["status_code"])

    if data["cookies"] is not None:
        response = add_cookies(response, data["cookies"])

    return response

