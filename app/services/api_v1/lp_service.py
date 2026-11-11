from fastapi import Cookie, Path
from fastapi.responses import Response
from functools import lru_cache
from typing import Annotated
import httpx

from common.settings import get_settings
from common.schemas import ResponseCookies, ProductVersion, create_response


cookies = Annotated[ResponseCookies | None, Cookie()]
cookie = Annotated[str | None, Cookie()]
d2l_resp = Annotated[tuple[dict,int] | tuple[str,int] | tuple[None,None], "Parametro Necesario"]
profile_id = Annotated[str, Path()]


class LPService():
    def __init__(self, product_version: ProductVersion):
        self.lp_version = product_version
        self.settings = get_settings()
        self.d2l_client = httpx.Client()
        self.url = f"{self.settings.get_api_url(1)}/lp/{self.lp_version}"


    def d2l_requests(self, req: str, url: str, access_token: cookie) -> d2l_resp:
        response = Response()

        match req:
            case "get":
                response = self.d2l_client.get(url=url,headers={"Authorization": f"Bearer {access_token}"})

        if "json" in response.headers.get("content-type", ""):
            return response.json(), response.status_code
        else:
            return response.text, response.status_code


    def whoami(self, access_token: cookie) -> Response:
        url = f"{self.url}/users/whoami"
        json_or_txt_response, resp_status = self.d2l_requests(req="get",url=url,access_token=access_token)

        response_data = {
            "status_code": resp_status,
            "content": json_or_txt_response,
            "cookies": None
        }

        return create_response(response_data)


    # NO TENGO PERMISOS
    def my_profile(self, ProfileIdentifier: profile_id, access_token: cookie) -> Response:
        url = f"{self.url}/profile/{ProfileIdentifier}"
        json_response, resp_status = self.d2l_requests(req="get", url=url, access_token=access_token)

        response_data = {
            "status_code": resp_status,
            "content": json_response,
            "cookies": None
        }

        return create_response(response_data)


    def myenrollments(self, access_token: cookie) -> Response:
        url = f"{self.url}/enrollments/myenrollments/"
        json_response, resp_status = self.d2l_requests(req="get",url=url,access_token=access_token)

        response_data = {
            "status_code": resp_status,
            "content": json_response,
            "cookies": None
        }

        return create_response(response_data)


@lru_cache()
def get_service(product_version: ProductVersion) -> LPService:
    return LPService(product_version)