import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "TaskEngine API"
    DATABASE_URL: str = "sqlite:///./taskengine.db"
    API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
