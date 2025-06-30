from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyHttpUrl, PostgresDsn
from functools import lru_cache
from typing_extensions import Self

class Settings(BaseSettings):
    PROJECT_NAME: str = "myapp"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(False, env="DEBUG")
    API_PREFIX: str = "/api"
    ALLOW_ORIGINS: list[AnyHttpUrl | str] = ["*"]
    db_url: PostgresDsn = Field(..., alias="DATABASE_URL")
    secret_key: str     = Field(..., alias="SECRET_KEY")
    algorithm: str      = Field("HS256", alias="ALGORITHM")

   
    class Config:
        env_file=".env"
        env_file_encoding="utf-8"
        populate_by_name=True
        extra="ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
