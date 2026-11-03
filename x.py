from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Lee variables de entorno y, si existe, el archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Tasks API"
    database_url: str = "sqlite:///./tasks.db"
    secret_key: str  # sin valor por defecto: si falta, la app NO arranca
    access_token_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    # lru_cache: se construye una sola vez y se reutiliza (parecido a un bean singleton)
    return Settings()
