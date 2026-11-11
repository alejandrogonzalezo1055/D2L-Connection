from fastapi import Path, HTTPException, status, Header
from fastapi.responses import Response, RedirectResponse, JSONResponse
from pydantic import BaseModel, field_validator
from typing import Annotated
import httpx
import secrets

from common.settings import get_settings


ProductVersion = Annotated[float | None, Path()]


def require_internal_key(authorization: Annotated[str | None, Header()] = None):
    ok = False
    if authorization and authorization.startswith("Bearer "):
        ok = secrets.compare_digest(authorization[7:], get_settings().python_api_key.get_secret_value())
    if not ok:
        raise HTTPException(status_code=401)


class ProductVersionValidator():
    def __init__(self, product: str):
        self.product = product

    async def __call__(self, product_version: ProductVersion) -> ProductVersion:
        url = get_settings().get_api_url(1)
        async with httpx.AsyncClient() as client:
            response = await client.get(url=f"{url}/versions/")
            json_response = response.json()

            product = next((p for p in json_response if p["ProductCode"] == self.product), None)

            if product:
                version = next((v for v in product["SupportedVersions"] if float(v) == product_version), None)
                if version:
                    product_version = version
                else:
                    raise HTTPException(
                        status_code=status.HTTP_406_NOT_ACCEPTABLE,
                        detail=f"La version de la peticion '{product_version}' no es valida"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El producto con codigo '{product["ProductCode"]}' no existe"
                )

        return product_version


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
            max_age=cookie["max_age"],
            secure=True # SOLO SE PUEDE ENVIAR POR HTTPS
        )

    return response


def delete_cookies(response: Response) -> Response:
    for cookie in ["auth_code", "oauth_state", "access_token", "refresh_token", "response_time"]:
        response.delete_cookie(key=cookie, secure=True)

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