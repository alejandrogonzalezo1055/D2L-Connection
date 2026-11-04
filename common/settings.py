from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Annotated
from functools import lru_cache


FrozenSecret = Annotated[SecretStr, Field(default=None, frozen=True)]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='common/.env',
        validate_assignment=True,
        hide_input_in_errors=True
    )
    mock_api_base_url: str = None
    mock_auth_base_url: str = None
    app_id: str = None
    app_secret: FrozenSecret
    app_scope: str = None

@lru_cache()
def get_settings() -> Settings:
    return Settings()