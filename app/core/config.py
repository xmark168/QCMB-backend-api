from pydantic_settings import BaseSettings
from pydantic import Field, AnyHttpUrl
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "myapp"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(False, env="DEBUG")
    API_PREFIX: str = "/api"
    ALLOW_ORIGINS: list[AnyHttpUrl | str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
