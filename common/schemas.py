from fastapi import Path, HTTPException, status
from fastapi.responses import Response, RedirectResponse, JSONResponse
from pydantic import BaseModel, field_validator
from typing import Final, Annotated
import httpx

from common.settings import get_settings


TOKEN_LIFE: Final[int] = 3600


lp_version = Annotated[float | None, Path(ge=1.0, le=1.64)]

def validate_version(version: lp_version) -> lp_version:
    url = get_settings().get_base_url(1)
    with httpx.Client() as client:
        response = client.get(f"{url}/version").json()

        product = next((p for p in response if p["ProductCode"] == "lp"), None)

        if product:
            product_version = next((v for v in product["SupportedVersions"] if float(v) == version), None)
            if product_version:
                version = product_version
            else:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail=f"La version de la peticion '{version}' no es valida"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El producto con codigo '{product["ProductCode"]}' no existe"
            )

    return version


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

