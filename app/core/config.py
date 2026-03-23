from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = False

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "deepseek/deepseek-chat"

    OPENAI_API_KEY: str

    GOOGLE_PLACES_API_KEY: str

    RATE_LIMIT_CHAT: int = 9999
    RATE_LIMIT_KUNDLI: int = 20
    RATE_LIMIT_WHISPER: int = 30
    RATE_LIMIT_TTS: int = 30

    ALLOWED_ORIGINS: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
