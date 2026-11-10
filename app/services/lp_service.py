from fastapi import Cookie
from fastapi.responses import Response
from functools import lru_cache
from typing import Annotated
import httpx

from common.settings import get_settings
from common.schemas import ResponseCookies, lp_version, create_response


cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
d2l_resp = Annotated[tuple[dict,int] | tuple[None,None], "Parametro Necesario"]

class LPService():
    def __init__(self, version: lp_version):
        self.lp_version = version
        self.settings = get_settings()
        self.d2l_client = httpx.Client()
        self.url = f"{self.settings.get_api_url(1)}/lp/{self.lp_version}"


    def d2l_get_whoami(self, access_token: cookie) -> d2l_resp:
        url = f"{self.url}/users/whoami"

        response = self.d2l_client.get(
            url=url,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        return response.json(), response.status_code

    def whoami(self, access_token: cookie) -> Response:
        json_response, resp_status = self.d2l_get_whoami(access_token)

        response_data = {
            "status_code": resp_status,
            "content": json_response,
            "cookies": None
        }

        return create_response(response_data)


@lru_cache()
def get_service(version: lp_version) -> LPService:
    return LPService(version)