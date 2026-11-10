from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Annotated, Final
from functools import lru_cache


FrozenSecret = Annotated[SecretStr, Field(default=None, frozen=True)]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='common/.env',
        validate_assignment=True,
        hide_input_in_errors=True
    )
    api_base_url: str = None
    auth_base_url: str = None
    app_id: str = None
    app_secret: FrozenSecret
    app_scope: str = None

    def get_api_url(self, option: int) -> str:
        url = ""
        match option:
            case 1:
                url = f"https://{self.api_base_url}/d2l/api"
            case 2:
                url = f"https://{self.api_base_url}/d2l"

        return url

    def get_oauth_url(self) -> str:
        return f"https://{self.auth_base_url}/oauth2/auth"

    def get_token_url(self) -> str:
        return f"https://{self.auth_base_url}/core/connect/token"

@lru_cache()
def get_settings() -> Settings:
    return Settings()