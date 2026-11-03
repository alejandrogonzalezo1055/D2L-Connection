from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv


class Settings(BaseSettings):

    env_config = SettingsConfigDict(env_file='.env')