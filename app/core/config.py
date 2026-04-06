"""
Core configuration and settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Finance Dashboard API"
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    DATABASE_URL: str = "sqlite:///./finance.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
