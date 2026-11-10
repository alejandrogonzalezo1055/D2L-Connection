from fastapi import Cookie
from fastapi.responses import Response
from functools import lru_cache
from typing import Annotated
import httpx

from common.settings import get_settings
from common.schemas import ResponseCookies, product_version, create_response


cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
d2l_resp = Annotated[tuple[dict,int] | tuple[None,None], "Parametro Necesario"]


class LEService():
    def __init__(self, version: product_version):
        self.le_version = version
        self.settings = get_settings()
        self.d2l_client = httpx.Client()
        self.url = f"{self.settings.get_api_url(1)}/le/{self.le_version}"


    def d2l_requests(self, req: str, access_token: cookie, url: str) -> d2l_resp:
        response = None

        match req:
            case "get":
                response = self.d2l_client.get(url=url,headers={"Authorization": f"Bearer {access_token}"})

        return response.json(), response.status_code


    def


@lru_cache()
def get_service(version: product_version) -> LEService:
    return LEService(version)